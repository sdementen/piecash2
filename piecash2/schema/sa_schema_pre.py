from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import lru_cache

import sqlalchemy
from sqlalchemy import select, text, union_all
from sqlalchemy.ext.declarative import declarative_base as declarative_base_
from sqlalchemy.ext.hybrid import Comparator, hybrid_property
from sqlalchemy.orm import DeclarativeMeta as DeclarativeMeta_, Session

from piecash2 import utils

# todo: reduce the list to classes which can really contains slots/recurrences to speed up detection of object class
klswithguid_names = [
    "Account",
    "Billterm",
    "Book",
    "Budget",
    "Commodity",
    "Customer",
    "Employee",
    "Entry",
    "Invoice",
    "Job",
    "Lot",
    "Order",
    "Price",
    "Schedxaction",
    "Slot",
    "Split",
    "Taxtable",
    "Transaction",
    "Vendor",
]


class SlotValueType(Enum):
    """Enum to define the type of owner"""

    INVALID = -1
    INT64 = 1
    DOUBLE = 2
    NUMERIC = 3
    STRING = 4
    GUID = 5
    TIME64 = 6
    PLACEHOLDER_DONT_USE = 7
    GLIST = 8
    FRAME = 9
    GDATE = 10


class OwnerType(Enum):
    """Enum to define the type of owner"""

    NONE = 0
    UNDEFINED = 1
    CUSTOMER = 2
    JOB = 3
    VENDOR = 4
    EMPLOYEE = 5

    @classmethod
    def from_cls(cls, obj):
        return cls[obj.__class__.__name__.upper()] if obj is not None else cls.NONE

    @property
    def cls_name(self):
        return self.attr_name.capitalize()

    @property
    def attr_name(self):
        return self.name.lower()

    @classmethod
    def object_classes(cls) -> list["OwnerType"]:
        return [cls for cls in cls if cls not in {cls.NONE, cls.UNDEFINED}]


class GuidComparator(Comparator):
    """Take a guid and compare it to another object's guid"""

    def __eq__(self, other):
        # Define custom comparison for equality
        return self.__clause_element__() == other.guid

    def __ne__(self, other):
        # Define custom comparison for inequality
        return self.__clause_element__() != other.guid


class DeclarativeMeta(DeclarativeMeta_):
    use_decimal = False

    def __new__(cls, name, bases, attrs):
        """
        The different objects use different naming conventions:
        - tablename = underscore plural
        - name = CamelCase singular
        - fields = underscore singular
        """

        tablename = attrs.get("__tablename__")

        if tablename:
            assert tablename == utils.underscore(utils.pluralize(name)), f"{tablename} <> {utils.underscore(utils.pluralize(name))}"

            self_id = attrs.get("guid", attrs.get("id"))

            for k, v in list(attrs.items()):
                if name == "Slot" and k == "obj_guid":
                    # replace name of column obj_guid to guid
                    attrs["guid"] = sqlalchemy.orm.synonym("guid_val")

                elif name in {"Slot", "Recurrence"} and k == "guid_val":
                    attrs_to_expire = []
                    # define the n relationships related to guid
                    for kls_other in klswithguid_names:
                        kwargs = dict(
                            argument=kls_other,
                            backref="slots",
                            primaryjoin=f"foreign({name}.obj_guid) == remote({kls_other}.guid)",
                            viewonly=True,
                        )
                        attr_name = f"object_val_{kls_other.lower()}"
                        attrs[attr_name] = sqlalchemy.orm.relationship(**kwargs)
                        attrs_to_expire.append(attr_name)

                    # define the object property
                    def object_getter(self):
                        session = Session.object_session(self)

                        # detect which type of class is the object related to the obj_guid
                        qry_object_type_attr = union_all(
                            *(
                                select(text(f"'{name.lower()}'")).where(kls.guid == self.obj_guid)
                                for name, kls in name2kls.items()  # noqa: F821
                            ),
                        ).limit(1)
                        object_type_attr = session.execute(qry_object_type_attr).scalar()

                        # return the object related to the obj_guid
                        return getattr(self, f"object_val_{object_type_attr}")

                    def object_comparator(cls):
                        return GuidComparator(cls.obj_guid)

                    def object_setter(self, object):
                        object_old = self.object
                        self.obj_guid = object.guid
                        # expire the relationships related to the attr
                        session = Session.object_session(self)
                        session.expire(self, attrs_to_expire)  # expire link Slot -> Object
                        session.expire(object_old, ["slots"])  # expire backrefs on old object
                        session.expire(object, ["slots"])  # expire backrefs on new object

                    attrs["object"] = object_getter
                    attrs["object"] = hybrid_property(object_getter).setter(object_setter).comparator(object_comparator)

                elif name == "Slot" and k == "slot_type":
                    # handle slot_type as enum via slot_type_enum
                    # todo: rename slot_type to _slot_type and slot_type_enum to slot_type
                    # todo: redefine slot_type to be an Enum type but using the same backed as original
                    @hybrid_property
                    def getter(self):
                        return SlotValueType(self.slot_type)

                    @getter.setter
                    def setter(self, value):
                        self.slot_type = value.value

                    @getter.expression
                    def expression(cls):
                        return cls.slot_type

                    attrs["slot_type_enum"] = getter

                # handle fractions/decimals as numerators/denominators
                elif k.endswith("_denom") and k[:-6] + "_num" in attrs:
                    fraction_base = k[:-6]
                    if cls.use_decimal:
                        attrs[f"{fraction_base}"] = hybrid_property(
                            lambda self: Decimal(getattr(self, fraction_base + "_num")) / Decimal(getattr(self, fraction_base + "_denom"))
                        ).setter(
                            lambda self, value: setattr(self, fraction_base + "_num", (ratio := value.as_integer_ratio())[0])
                            or setattr(self, fraction_base + "_denom", ratio[1])
                        )
                    else:
                        attrs[f"{fraction_base}"] = hybrid_property(
                            lambda self: Fraction(getattr(self, fraction_base + "_num"), getattr(self, fraction_base + "_denom"))
                        ).setter(
                            lambda self, value: setattr(self, fraction_base + "_num", value.numerator)
                            or setattr(self, fraction_base + "_denom", value.denominator)
                        )

                # handle owner/billto _guid/_type combo
                elif k.endswith("_guid") and k[:-5] + "_type" in attrs:
                    # define the n relationships related to OwnerTypes
                    # and the appropriate python getter/setter and SQL comparator
                    attr = k[:-5]
                    assert attr in {"billto", "owner"}, attr

                    for typ in OwnerType:
                        if typ in {OwnerType.NONE, OwnerType.UNDEFINED}:
                            continue
                        kls_other = typ.cls_name
                        kwargs = dict(
                            argument=kls_other,
                            backref=None,
                            primaryjoin=f"(foreign({name}.{attr}_guid) == remote({kls_other}.guid)) "
                            f"& ({name}.{attr}_type == {typ.value})",
                            viewonly=True,
                        )
                        attrs[f"{attr}_{typ.attr_name}"] = sqlalchemy.orm.relationship(**kwargs)

                    def attr_getter(self, attr=attr):
                        typ = OwnerType(getattr(self, f"{attr}_type") or 0)

                        if typ in OwnerType.object_classes():
                            return getattr(self, f"{attr}_{typ.attr_name}")
                        else:
                            return None

                    def attr_comparator(cls, attr=attr):
                        return GuidComparator(getattr(cls, f"{attr}_guid"))

                    def attr_setter(
                        self, value, attr=attr, attrs_to_expire=tuple(f"{attr}_{kls.attr_name}" for kls in OwnerType.object_classes())
                    ):
                        typ = OwnerType.from_cls(value)
                        setattr(self, f"{attr}_guid", value.guid)
                        setattr(self, f"{attr}_type", typ.value)
                        # expire the relationships related to the attr
                        Session.object_session(self).expire(self, attrs_to_expire)

                    attrs[f"{attr}"] = hybrid_property(attr_getter).setter(attr_setter).comparator(attr_comparator)

                # create relationships through xxx_guid
                elif k.endswith("_guid"):
                    obj_name = k[:-5]

                    kls_self = name
                    kls_other = utils.camelize(obj_name, uppercase_first_letter=True)
                    backref = utils.pluralize(utils.underscore(kls_self))

                    if kls_other == "Parent" and kls_self == "Account":
                        backref = sqlalchemy.orm.backref("parent", remote_side=[self_id])
                        kls_other = kls_self
                        obj_name = "children"
                    if kls_other in {"RootAccount", "RootTemplate"}:
                        kls_other = "Account"
                        backref = None
                    if kls_other == "Currency":
                        kls_other = "Commodity"
                        backref = None
                    if kls_other == "TemplateAct":
                        kls_other = "Account"
                    if kls_other == "Tx":
                        kls_other = "Transaction"

                    if obj_name == "ccard":  # credit car account
                        kls_other = "Account"
                    if f"{obj_name}_type" in attrs:  # x_guid to be used with x_type in Entries/Invoicing/...
                        print(tablename, obj_name)
                        for kls_other in cls.classes_with_guid:
                            kls_other = kls_other.__name__
                            kwargs = dict(
                                argument=kls_other,
                                backref=None,
                                primaryjoin=f"foreign({kls_self}.{k}) == {kls_other}.guid",
                                viewonly=True,
                            )
                            attrs[f"{obj_name}_{kls_other}"] = sqlalchemy.orm.relationship(**kwargs)

                        continue
                    if obj_name == "obj" and kls_self in {"Recurrence", "Slot"}:
                        # done via ObjGUIDMixin
                        continue

                    kwargs = dict(
                        argument=kls_other,
                        backref=backref,
                        primaryjoin=f"foreign({kls_self}.{k}) == {kls_other}.guid",
                    )

                    attrs[obj_name] = sqlalchemy.orm.relationship(**kwargs)

        self = super().__new__(cls, name, bases, attrs)

        return self


class Base:
    def __hash__(self):
        return hash((self.__class__.__name__, self.id))

    def __eq__(self, other):
        return isinstance(other, self.__class__) and ((self.__class__.__name__, self.id)) == ((other.__class__.__name__, other.id))

    def __repr__(self):
        return f"{self.__class__.__name__}<{self.name if hasattr(self, 'name') else ''}>[{self.uid}]"

    @property
    def uid(self):
        """Property to return the id if no Column with id already exists"""
        try:
            return self.guid
        except AttributeError:
            return self.id

    @property
    def id(self):
        """Property to return the id if no Column with id already exists"""
        return self.guid


@lru_cache
def declarative_base(*args, **kwargs):
    base = declarative_base_(*args, **kwargs, metaclass=DeclarativeMeta, cls=Base)
    return base
