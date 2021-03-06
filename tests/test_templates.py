# Copyright (c) DPU AUTHORS, under the terms and conditions of the GPL-2+
# license.
"""
This module contains tests for the template system.
"""

from dpu.templates import (PlainTemplate, JinjaTemplate,
                           DebianShim, UpstreamShim,
                           TemplateManager)

from dpu.utils import tmpdir, cd, mkdir, abspath
import os.path
import os


def assert_content(path, content):
    """
    Ensure the content is what we think it is.
    """
    content_obj = open(path, 'r').read().strip()
    if content != content_obj:
        print "Path: %s" % (path)
        print "Expt: %s" % (content)
        print "Got:  %s" % (content_obj)

    assert content == content_obj


def test_jinja2_context():
    tpl = JinjaTemplate("tests/resources/templates/jinja1")
    with tmpdir() as tmp:
        try:
            tpl.render(tmp)
            assert True is False
        except ValueError:
            pass


def test_plain_template_basic():
    """
    Ensure basic sanity with the PlainTemplate system.
    """
    with tmpdir() as tmp:
        pt1 = PlainTemplate("tests/resources/templates/plain1")
        pt1.render(tmp)
        with cd(tmp):
            for x in ['foo', 'bar', 'baz']:
                assert_content(x, x)


def test_plain_template_advanced():
    """
    Ensure sanity when two PlainTemplates are rendered together,
    along with a directory.
    """
    with tmpdir() as tmp:
        pt1 = PlainTemplate("tests/resources/templates/plain1")
        pt2 = PlainTemplate("tests/resources/templates/plain2")
        pt1.render(tmp)
        pt2.render(tmp)

        values = {
            "foo": "foo",
            "bar": "not bar",
            "baz": "baz",
            "kruft/flip": "flip"
        }

        with cd(tmp):
            for entry in values:
                content = values[entry]
                assert_content(entry, content)


def test_jinja_template_basic():
    """
    Ensure basic Jinja sanity.
    """
    with tmpdir() as tmp:
        jt1 = JinjaTemplate("tests/resources/templates/jinja1")

        context = {
            "foo": "foo1",
            "kruft": "kruft1",
            "plop": "plop1"
        }

        jt1.set_context(context)
        jt1.render(tmp)

        with cd(tmp):
            for x in context:
                if not os.path.exists(x):
                    assert os.path.exists(x)

            for entry in context:
                assert_content(entry, context[entry])


def test_jinja_template_advanced():
    """
    Ensure multi-Jinja sanity, as well as nested files.
    """
    with tmpdir() as tmp:
        jt1 = JinjaTemplate("tests/resources/templates/jinja1")
        jt2 = JinjaTemplate("tests/resources/templates/jinja2")

        context = {
            "foo": "foo1",
            "kruft": "kruft1",
            "plop": "plop1",
            "no": "no",
            "go": "go",
        }

        jt1.set_context(context)
        jt2.set_context(context)
        jt1.render(tmp)
        jt2.render(tmp)

        files = {
            "literal": "{{literal}}",
            "really/nested/directory/with/a/file/foo": context['foo'],
            "kruft": context['kruft'],
            "foo": context['foo'],
            "nogo": "%s %s" % (context['no'], context['go']),
            "plop": context['plop']
        }

        with cd(tmp):
            for f in files:
                assert_content(f, files[f])


def test_debian_shim_blank():
    """
    Ensure the DebianShim won't error when the directory doesn't have a
    debdir present.
    """
    with tmpdir() as tmp:
        ds = DebianShim()
        ds.render(tmp)


def test_debian_shim_there():
    """
    Ensure the shim removes the Debian directory, if it exists, and it can be
    run over the same thing more then once.
    """
    with tmpdir() as tmp:
        debdir = "%s/debian" % (tmp)
        mkdir(debdir)
        assert os.path.exists(debdir)
        ds = DebianShim()
        ds.render(tmp)
        assert not os.path.exists(debdir)
        ds.render(tmp)


def test_debian_shim_there_two():
    """
    Ensure the Debian shim won't remove files other then the Debian/
    directory.
    """
    with tmpdir() as tmp:
        debdir = "%s/debian" % (tmp)
        testfd = "%s/foo" % (tmp)
        mkdir(debdir)
        open(testfd, 'w').close()
        assert os.path.exists(debdir)
        assert os.path.exists(testfd)
        ds = DebianShim()
        ds.render(tmp)
        assert not os.path.exists(debdir)
        assert os.path.exists(testfd)
        ds.render(tmp)


def test_upstream_shim():
    """
    Ensure we create a debian tarball thinger.
    """
    pkgname = "testpkg-name"
    version = "1.0"
    with tmpdir() as tmp:
        with cd(tmp):
            mkdir("%s-%s" % (pkgname, version))
        tmp += "/%s-%s" % (pkgname, version)
        uss = UpstreamShim(pkgname, version)
        uss.set_compression("gzip")
        uss.render(tmp)
        assert "%s/%s_%s.orig.tar.gz" % (tmp, pkgname, version)
        assert "%s/%s-%s" % (tmp, pkgname, version)


def test_template_voodoo():
    """
    Make sure the getattr hack still works right.
    """
    templs = {
        "PlainTemplate": PlainTemplate,
        "JinjaTemplate": JinjaTemplate,
        "DebianShim": DebianShim,
        "UpstreamShim": UpstreamShim,
        "FakeName": None
    }
    tplm = TemplateManager()
    for templ in templs:
        assert tplm._get_template(templ) == templs[templ]


def test_template_manager_error():
    """
    Make sure that we error out with a bad template.
    """
    tm = TemplateManager()
    try:
        tm.add_template("foo")
        assert True is False
    except ValueError:
        pass


def test_template_manager():
    """
    Make sure the template manager basics work right.
    """
    template_dir = abspath("./tests/resources/templates/")
    templs = {
        "plain1": "PlainTemplate",
        "jinja1": "JinjaTemplate",
        "jinja2": "JinjaTemplate"
    }
    context = {
        "foo": "foo"
    }
    with tmpdir() as tmp:
        tplm = TemplateManager()
        for template in templs:
            kwargs = {}
            klasse = templs[template]
            if klasse == "JinjaTemplate":
                kwargs['context'] = context

            tplm.add_template(klasse, os.path.join(template_dir, template),
                              **kwargs)

        tplm.render(tmp)


def test_real_template_thing():
    """
    Make sure None templates throw errors
    """
    tm = TemplateManager()
    try:
        tm.add_real_template(None)
        assert True is False
    except ValueError:
        pass
