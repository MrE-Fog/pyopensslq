"""
Unit tests for L{OpenSSL.crypto}.
"""

from unittest import TestCase

from OpenSSL.crypto import TYPE_RSA, TYPE_DSA, Error, PKey, PKeyType
from OpenSSL.crypto import X509, X509Name, X509NameType


class _Python23TestCaseHelper:
    # Python 2.3 compatibility.
    def assertTrue(self, *a, **kw):
        return self.failUnless(*a, **kw)


class PKeyTests(TestCase, _Python23TestCaseHelper):
    """
    Unit tests for L{OpenSSL.crypto.PKey}.
    """
    def test_construction(self):
        """
        L{PKey} takes no arguments and returns a new L{PKeyType} instance.
        """
        self.assertRaises(TypeError, PKey, None)
        key = PKey()
        self.assertTrue(
            isinstance(key, PKeyType),
            "%r is of type %r, should be %r" % (key, type(key), PKeyType))


    def test_pregeneration(self):
        """
        L{PKeyType.bits} and L{PKeyType.type} return C{0} before the key is
        generated.
        """
        key = PKey()
        self.assertEqual(key.type(), 0)
        self.assertEqual(key.bits(), 0)


    def test_failedGeneration(self):
        """
        L{PKeyType.generate_key} takes two arguments, the first giving the key
        type as one of L{TYPE_RSA} or L{TYPE_DSA} and the second giving the
        number of bits to generate.  If an invalid type is specified or
        generation fails, L{Error} is raised.  If an invalid number of bits is
        specified, L{ValueError} or L{Error} is raised.
        """
        key = PKey()
        self.assertRaises(TypeError, key.generate_key)
        self.assertRaises(TypeError, key.generate_key, 1, 2, 3)
        self.assertRaises(TypeError, key.generate_key, "foo", "bar")
        self.assertRaises(Error, key.generate_key, -1, 0)

        self.assertRaises(ValueError, key.generate_key, TYPE_RSA, -1)
        self.assertRaises(ValueError, key.generate_key, TYPE_RSA, 0)

        # XXX RSA generation for small values of bits is fairly buggy in a wide
        # range of OpenSSL versions.  I need to figure out what the safe lower
        # bound for a reasonable number of OpenSSL versions is and explicitly
        # check for that in the wrapper.  The failure behavior is typically an
        # infinite loop inside OpenSSL.

        # self.assertRaises(Error, key.generate_key, TYPE_RSA, 2)

        # XXX DSA generation seems happy with any number of bits.  The DSS
        # says bits must be between 512 and 1024 inclusive.  OpenSSL's DSA
        # generator doesn't seem to care about the upper limit at all.  For
        # the lower limit, it uses 512 if anything smaller is specified.
        # So, it doesn't seem possible to make generate_key fail for
        # TYPE_DSA with a bits argument which is at least an int.

        # self.assertRaises(Error, key.generate_key, TYPE_DSA, -7)


    def test_rsaGeneration(self):
        """
        L{PKeyType.generate_key} generates an RSA key when passed
        L{TYPE_RSA} as a type and a reasonable number of bits.
        """
        bits = 128
        key = PKey()
        key.generate_key(TYPE_RSA, bits)
        self.assertEqual(key.type(), TYPE_RSA)
        self.assertEqual(key.bits(), bits)


    def test_dsaGeneration(self):
        """
        L{PKeyType.generate_key} generates a DSA key when passed
        L{TYPE_DSA} as a type and a reasonable number of bits.
        """
        # 512 is a magic number.  The DSS (Digital Signature Standard)
        # allows a minimum of 512 bits for DSA.  DSA_generate_parameters
        # will silently promote any value below 512 to 512.
        bits = 512
        key = PKey()
        key.generate_key(TYPE_DSA, bits)
        self.assertEqual(key.type(), TYPE_DSA)
        self.assertEqual(key.bits(), bits)


    def test_regeneration(self):
        """
        L{PKeyType.generate_key} can be called multiple times on the same
        key to generate new keys.
        """
        key = PKey()
        for type, bits in [(TYPE_RSA, 512), (TYPE_DSA, 576)]:
             key.generate_key(type, bits)
             self.assertEqual(key.type(), type)
             self.assertEqual(key.bits(), bits)



class X509NameTests(TestCase, _Python23TestCaseHelper):
    """
    Unit tests for L{OpenSSL.crypto.X509Name}.
    """
    def _x509name(self, **attrs):
        # XXX There's no other way to get a new X509Name yet.
        name = X509().get_subject()
        attrs = attrs.items()
        # Make the order stable - order matters!
        attrs.sort(lambda (k1, v1), (k2, v2): cmp(v1, v2))
        for k, v in attrs:
            setattr(name, k, v)
        return name


    def test_attributes(self):
        """
        L{X509NameType} instances have attributes for each standard (?)
        X509Name field.
        """
        name = self._x509name()
        name.commonName = "foo"
        self.assertEqual(name.commonName, "foo")
        self.assertEqual(name.CN, "foo")
        name.CN = "baz"
        self.assertEqual(name.commonName, "baz")
        self.assertEqual(name.CN, "baz")
        name.commonName = "bar"
        self.assertEqual(name.commonName, "bar")
        self.assertEqual(name.CN, "bar")
        name.CN = "quux"
        self.assertEqual(name.commonName, "quux")
        self.assertEqual(name.CN, "quux")


    def test_copy(self):
        """
        L{X509Name} creates a new L{X509NameType} instance with all the same
        attributes as an existing L{X509NameType} instance when called with
        one.
        """
        name = self._x509name(commonName="foo", emailAddress="bar@example.com")

        copy = X509Name(name)
        self.assertEqual(copy.commonName, "foo")
        self.assertEqual(copy.emailAddress, "bar@example.com")

        # Mutate the copy and ensure the original is unmodified.
        copy.commonName = "baz"
        self.assertEqual(name.commonName, "foo")

        # Mutate the original and ensure the copy is unmodified.
        name.emailAddress = "quux@example.com"
        self.assertEqual(copy.emailAddress, "bar@example.com")


    def test_repr(self):
        """
        L{repr} passed an L{X509NameType} instance should return a string
        containing a description of the type and the NIDs which have been set
        on it.
        """
        name = self._x509name(commonName="foo", emailAddress="bar")
        self.assertEqual(
            repr(name),
            "<X509Name object '/emailAddress=bar/CN=foo'>")


    def test_comparison(self):
        """
        L{X509NameType} instances should compare based on their NIDs.
        """
        def _equality(a, b, assertTrue, assertFalse):
            assertTrue(a == b, "(%r == %r) --> False" % (a, b))
            assertFalse(a != b)
            assertTrue(b == a)
            assertFalse(b != a)

        def assertEqual(a, b):
            _equality(a, b, self.assertTrue, self.assertFalse)

        # Instances compare equal to themselves.
        name = self._x509name()
        assertEqual(name, name)

        # Empty instances should compare equal to each other.
        assertEqual(self._x509name(), self._x509name())

        # Instances with equal NIDs should compare equal to each other.
        assertEqual(self._x509name(commonName="foo"),
                    self._x509name(commonName="foo"))

        # Instance with equal NIDs set using different aliases should compare
        # equal to each other.
        assertEqual(self._x509name(commonName="foo"),
                    self._x509name(CN="foo"))

        # Instances with more than one NID with the same values should compare
        # equal to each other.
        assertEqual(self._x509name(CN="foo", organizationalUnitName="bar"),
                    self._x509name(commonName="foo", OU="bar"))

        def assertNotEqual(a, b):
            _equality(a, b, self.assertFalse, self.assertTrue)

        # Instances with different values for the same NID should not compare
        # equal to each other.
        assertNotEqual(self._x509name(CN="foo"),
                       self._x509name(CN="bar"))

        # Instances with different NIDs should not compare equal to each other.
        assertNotEqual(self._x509name(CN="foo"),
                       self._x509name(OU="foo"))

        def _inequality(a, b, assertTrue, assertFalse):
            assertTrue(a < b)
            assertTrue(a <= b)
            assertTrue(b > a)
            assertTrue(b >= a)
            assertFalse(a > b)
            assertFalse(a >= b)
            assertFalse(b < a)
            assertFalse(b <= a)

        def assertLessThan(a, b):
            _inequality(a, b, self.assertTrue, self.assertFalse)

        # An X509Name with a NID with a value which sorts less than the value
        # of the same NID on another X509Name compares less than the other
        # X509Name.
        assertLessThan(self._x509name(CN="abc"),
                       self._x509name(CN="def"))

        def assertGreaterThan(a, b):
            _inequality(a, b, self.assertFalse, self.assertTrue)

        # An X509Name with a NID with a value which sorts greater than the
        # value of the same NID on another X509Name compares greater than the
        # other X509Name.
        assertGreaterThan(self._x509name(CN="def"),
                          self._x509name(CN="abc"))