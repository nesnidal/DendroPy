#! /usr/bin/env python

###############################################################################
##  DendroPy Phylogenetic Computing Library.
##
##  Copyright 2009 Jeet Sukumaran and Mark T. Holder.
##
##  This program is free software; you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation; either version 3 of the License, or
##  (at your option) any later version.
##
##  This program is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License along
##  with this program. If not, see <http://www.gnu.org/licenses/>.
##
###############################################################################

"""
This module provides classes and methods for managing taxa.
"""

import sys
import math
from dendropy.dataobject import base
from dendropy.utility import texttools
from dendropy.utility import containers

def new_taxon_set(ntax=10, label_func=None):
    """
    Generates a new set of Taxon objects. `label_func` should be a function
    which can take an integer representing a new Taxon object's index in the
    new TaxonSet as an argument and return an appropriate (unique) label for
    the taxon. Note that an alternative way of instantiating a set of taxa
    would be to call `TaxonSet` with a list of labels as an argument.
    """
    taxon_set = TaxonSet()
    if label_func is None:
        label_idx_length = int(math.log(ntax, 10)) + 1
        label_template = "T%%0%dd" % (label_idx_length)
        label_func = lambda x: label_template % x
    for i in range(ntax):
        taxon_set.new_taxon(label=label_func(i+1))
    return taxon_set

class TaxonLinked(base.IdTagged):
    """
    Provides infrastructure for maintaining link/reference to a Taxon
    object.
    """

    def __init__(self, taxon=None, label=None, oid=None, **kwargs):
        "Initializes by calling base class."
        base.IdTagged.__init__(self, oid=oid, label=label)
        self._taxon = taxon

    def _get_taxon(self):
        "Returns taxon associated with this object."
        return self._taxon

    def _set_taxon(self, taxon):
        """
        If `taxon` is a Taxon object, then it is assigned directly. If
        `taxon` is a string, then it is assumed to be a label, and a
        new taxon object is constructed based on it and assigned (the
        new taxon object will have the string given by `taxon` as id
        and label, though it will be moTaxonSetdified as neccessary to make it
        xs:NCName compliant for the id.
        """
        if taxon is None or isinstance(taxon, Taxon):
            self._taxon = taxon
        else:
            taxon_obj = Taxon()
            taxon_obj.label = taxon
            taxon_obj.oid = taxon
            self._taxon = taxon_obj

    taxon = property(_get_taxon, _set_taxon)

class TaxonSetLinked(base.IdTagged):
    """
    Provides infrastructure for the maintenance of references to taxa.
    """

    def __init__(self, taxon_set=None, label=None, oid=None):
        "Initializes by calling base class."
        base.IdTagged.__init__(self, label=label, oid=oid)
        self.taxon_set = taxon_set if taxon_set is not None else TaxonSet()

    def reindex_taxa(self, taxon_set=None, clear=True):
        """
        Rebuilds `taxon_set` from scratch, or assigns `Taxon` objects from
        given `TaxonSet` object `taxon_set` based on label values. Calls
        on `self.reindex_member_taxa()` to synchronize taxa.
        """
        if taxon_set is not None:
            self.taxon_set = taxon_set
        if clear:
            self.taxon_set.clear()
        self.reindex_subcomponent_taxa()
        return self.taxon_set

    def reindex_subcomponent_taxa():
        """
        Derived classes should override this to ensure that their various
        components, attributes and members all refer to the same `TaxonSet`
        object as `self.taxon_set`, and that `self.taxon_set` has all
        the `Taxon` objects in the various members.
        """
        pass

class TaxonSet(containers.OrderedSet, base.IdTagged):
    """
    Primary manager for collections of `Taxon` objects.
    """

    def _to_taxon(s):
        if isinstance(s, Taxon):
            return s
        if isinstance(s, str):
            return Taxon(label=s)
        raise ValueError("Cannot convert %s to Taxon" % str(s))
    _to_taxon = staticmethod(_to_taxon)

    def __init__(self, *args, **kwargs):
        """
        Handles keyword arguments: `oid` and `label`. If an iterable is passed
        as the first argument, then for every string in the iterable a Taxon
        object with the string is constructed and added to the set, while for
        every Taxon object in the iterable a new (distinct) Taxon object with the
        same label is constructed and added to the set.
        """
        la = len(args)
        if la > 0:
            if la > 1:
                raise TypeError("TaxonSet() takes at most 1 non-keyword argument %d were given" % la)
            containers.OrderedSet.__init__(self, [TaxonSet._to_taxon(i) for i in args[0]])
        else:
            containers.OrderedSet.__init__(self)
        base.IdTagged.__init__(self, oid=kwargs.get('oid'), label=kwargs.get('label'))
        self._is_mutable = kwargs.get('is_mutable', True) # immutable constraints not fully implemented -- only enforced at the add_taxon stage)

    def __deepcopy__(self, memo):
        o = self.__class__(list(self), label=self.label, is_mutable=self._is_mutable)
        memo[id(self)] = o
        return o

    def lock(self):
        self._is_mutable = False

    def unlock(self):
        self._is_mutable = True

    def get_is_locked(self):
        return self._is_mutable

    def set_is_locked(self, v):
        self._is_mutable = bool(v)
    is_locked = property(get_is_locked, set_is_locked)

    def __str__(self):
        "String representation of self."
        header = []
        if self.oid:
            header.append("%s" % str(self.oid))
        if self.label:
            header.append("('%s')" % self.label)
        taxlist = []
        for taxon in self:
            taxlist.append(str(taxon))
        return ' '.join(header) + ' : [' + ', '.join(taxlist) + ']'

    def get_taxon(self, label=None, taxon_required=True, oid=None):
        """
        Retrieves taxon object with given id OR label (if both are
        given, the first match found is returned). If taxon does not
        exist and update is False, an exception is raised. If taxon
        does not exist and update is True, then a new taxon is
        created, added, and returned.
        """
        update = self._is_mutable
        if not oid and not label:
            raise Exception("Need to specify DataObject ID or Label.")
        for taxon in self:
            if taxon.oid == oid or taxon.label == label:
                return taxon
        if taxon_required:
            if not update:
                raise Exception("Taxon not found: %s/%s" % (oid, label))
            taxon = Taxon(label=label, oid=oid)
            self.add(taxon)
            return taxon
        return None

    def add_taxon(self, taxon):
        """
        Adds taxon to self.
        """
        self.add(taxon)

    def new_taxon(self, label=None, oid=None, error_if_label_exists=False):
        "Creates and add a new `Taxon` if not already in the taxon index."
        if not self._is_mutable:
            raise Exception("Taxon %s:'%s' cannot be added to an immutable taxon index." % (oid, label))
        if error_if_label_exists and self.get_taxon(label=label, taxon_required=False) is not None:
            raise Exception("Taxon with label %s:'%s' already definied in the taxon index." % (oid, label))
        taxon = Taxon(label=label, oid=oid)
        self.add(taxon)
        return taxon

    def clear(self):
        "Removes all taxa from this list."
        for t in self:
            self.remove(t)

    def labels(self):
        "Convenience method to return all taxa labels."
        return [str(taxon.label) for taxon in self]

    def complement_split_bitmask(self, split):
        "Returns complement of the split bitmask."
        return (~split) & self.all_taxa_bitmask()

    def all_taxa_bitmask(self):
        "Returns mask of all taxa."
        #return pow(2, len(self)) - 1
        b = 1 << len(self)
        return b - 1

    def taxon_bitmask(self, taxon):
        """
        Returns unique bitmask of given taxon. Will raise index error if
        taxon does not exist.
        """
        try:
            return taxon.clade_mask
        except AttributeError:
            pass
        try:
            i = self.index(taxon)
            m = 1 << i
            taxon.clade_mask = m
            return m
        except ValueError:
            raise ValueError("Taxon with ID '%s' and label '%s' not found"
                             % (str(taxon.oid), str(taxon.label)))

    def split_bitmask_string(self, split_bitmask):
        "Returns bitstring representation of split_bitmask."
        return "%s" % texttools.int_to_bitstring(split_bitmask).rjust(len(self), "0")

class Taxon(base.IdTagged):
    """
    A taxon associated with a sequence or a node on a tree.
    """

    def __deepcopy__(self, memo):
        "Should not be copied"
        memo[id(self)] = self
        return self

    def cmp(taxon1, taxon2):
        "Compares taxon1 and taxon2 based on label."
        return cmp(str(taxon1.label), str(taxon2.label))

    cmp = staticmethod(cmp)

    def __init__(self, label=None, oid=None):
        "Initializes by calling base class."
        base.IdTagged.__init__(self, label=label, oid=oid)

    def __str__(self):
        "String representation of self = taxon name."
        return str(self.label)

    def __repr__(self):
        return "<DendroPy Taxon: '%s'>" % (str(self.label))
