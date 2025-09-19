from django.template import Context, Template
from decimal import Decimal
from django.test import SimpleTestCase


class FormatNumberFilterTests(SimpleTestCase):
    def render(self, expr, ctx=None):
        t = Template('{% load format_filters %}' + expr)
        return t.render(Context(ctx or {})).strip()

    def test_integer_formats(self):
        out = self.render("{{ val|format_number }}", {"val": 1234567})
        self.assertEqual(out, '1,234,567')

    def test_float_rounds_and_formats(self):
        out = self.render("{{ val|format_number }}", {"val": 12345.67})
        self.assertEqual(out, '12,346')

    def test_decimal_rounding(self):
        out = self.render("{{ val|format_number }}", {"val": Decimal('999.5')})
        self.assertEqual(out, '1,000')

    def test_none_returns_zero_string(self):
        out = self.render("{{ val|format_number }}", {"val": None})
        self.assertEqual(out, '0')

    def test_non_numeric_pass_through(self):
        out = self.render("{{ val|format_number }}", {"val": 'N/A'})
        self.assertEqual(out, 'N/A')
