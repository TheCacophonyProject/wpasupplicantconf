from collections import OrderedDict
from io import StringIO
from textwrap import dedent

import pytest

from wpasupplicantconf import WpaSupplicantConf, ParseError


def test_empty():
    conf = WpaSupplicantConf(StringIO(""))
    assert conf.fields() == {}
    assert conf.networks() == {}


def test_fields():
    inp = StringIO(
        dedent("""\
        country=NZ
        ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
        update_config = 1
        """))

    conf = WpaSupplicantConf(inp)

    assert conf.fields() == OrderedDict([
        ("country", "NZ"),
        ("ctrl_interface", "DIR=/var/run/wpa_supplicant GROUP=netdev"),
        ("update_config", "1"),
    ])
    assert conf.networks() == {}


def test_blank_lines():
    inp = StringIO(dedent("""\
        foo=1

        bar=2

        """))

    conf = WpaSupplicantConf(inp)

    assert conf.fields() == OrderedDict([
        ("foo", "1"),
        ("bar", "2"),
    ])


def test_invalid_line():
    with pytest.raises(ParseError):
        WpaSupplicantConf(StringIO("foo"))


def test_comments():
    inp = StringIO(
        dedent("""\
        # This should be ignored.
        country=NZ
        # So should this.
        """))

    conf = WpaSupplicantConf(inp)

    assert conf.fields() == OrderedDict([
        ("country", "NZ"),
    ])


def test_networks():
    inp = StringIO(
        dedent("""\
        network={
           ssid="foo bar"
           psk="secret"
           eap=TLS
        }

        network = {
           ssid="nsa"
           psk="password"
           scan_ssid = 1
        }
        """))

    conf = WpaSupplicantConf(inp)

    assert conf.fields() == {}
    assert conf.networks() == OrderedDict([
        ('foo bar', OrderedDict([
            ("psk", '"secret"'),
            ("eap", "TLS"),
        ])),
        ('nsa', OrderedDict([
            ("psk", '"password"'),
            ("scan_ssid", "1"),
        ])),
    ])


def test_no_ssid():
    inp = StringIO(
        dedent("""\
        network={
           psk="secret"
        }
        """))
    with pytest.raises(ParseError, match='missing "ssid" for network'):
        WpaSupplicantConf(inp)


def test_unknown_section_type():
    inp = StringIO(
        dedent("""\
        banana={
           fruit=yes
        }
        """))
    with pytest.raises(ParseError, match='unsupported section: "banana"'):
        WpaSupplicantConf(inp)


def test_full_config():
    inp = StringIO(
        dedent("""\
        country=NZ

        network={
           ssid="foo bar"
           psk="secret"
           eap=TLS
        }

        update_config = 1
        """))

    conf = WpaSupplicantConf(inp)

    assert conf.fields() == OrderedDict([
        ("country", "NZ"),
        ("update_config", "1"),
    ])
    assert conf.networks() == OrderedDict([
        ('foo bar', OrderedDict([
            ("psk", '"secret"'),
            ("eap", "TLS"),
        ])),
    ])


def test_nested_network():
    inp = StringIO(
        dedent("""\
        network={
           ssid="foo bar"
           network={
               ssid="blah"
           }
        }
        """))
    with pytest.raises(ParseError, match="can't nest networks"):
        WpaSupplicantConf(inp)


def test_add_network():
    inp = StringIO(
        dedent("""\
        network={
           ssid="foo bar"
           psk="secret"
        }
        """))
    conf = WpaSupplicantConf(inp)

    conf.add_network("another", psk="hi")

    assert conf.networks() == OrderedDict([
        ('foo bar', {
            "psk": '"secret"'
        }),
        ('another', {
            "psk": "hi"
        }),
    ])


def test_remove_network():
    inp = StringIO(
        dedent("""\
        network={
           ssid="foo"
           psk="foopass"
        }
        network={
           ssid="bar"
           psk="barpass"
        }
        """))
    conf = WpaSupplicantConf(inp)

    conf.remove_network("bar")
    assert conf.networks() == OrderedDict([
        ('foo', {
            "psk": '"foopass"'
        }),
    ])

    conf.remove_network("foo")
    assert conf.networks() == {}

    conf.remove_network("does not exist")
    assert conf.networks() == {}


def test_write():
    inp = StringIO(
        dedent("""\
        country=NZ
        ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
        update_config = 1
        """))
    conf = WpaSupplicantConf(inp)

    conf.add_network("foo", psk='"foo pass"', wow='man')
    conf.add_network("bar", psk='"bar pass"')

    out = StringIO()
    conf.write(out)

    assert out.getvalue() == """\
country=NZ
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={
    ssid="foo"
    psk="foo pass"
    wow=man
}

network={
    ssid="bar"
    psk="bar pass"
}
"""
