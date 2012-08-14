# Copyright (c) GNU GPL-2+, dpu-test-framework authors.

import os
import tarfile
import subprocess
from contextlib import contextmanager


def make_orig_tarball(rundir, upname, upversion, compression="gzip", outputdir=None):
    """Create an orig tarball in the rundir

    This function will create a tarball suitable for being used as an
    "upstream" tarball for a non-native package.  The source of the
    tarball will be the directory called "%(upname)s-%(upversion)",
    which must exists in rundir.

    The tarball will be created in outputdir and will be named
    according to dpkg-source's expectation.  If outputdir is not
    specified, it defaults to rundir.

    The optional "compression" parameter can be used to choose the
    compression of the tarball.  Supported values are "gzip", "bzip2",
    "xz" and "lzma".  NB: For non-native 1.0 source packages, only
    "gzip" should be used.

    Caveat: The function assumes anything in the "source" directory to
    be a part of the "upstream code".  Thus, if a debian/ dir is
    present it will be a part of the "upstream" tarball.
    """
    unpackdir = "%s-%s" % (upname, upversion)
    unpackpath = os.path.join(rundir, unpackdir)
    if outputdir is None:
        outputdir = rundir
    orig_tarball = os.path.join(outputdir, "%s_%s.orig.tar" % (upname, upversion))
    with _open_writeable_tarfile(orig_tarball, compression) as tarobj:
        tarobj.add(unpackpath, arcname=unpackdir)


@contextmanager
def open_compressed_tarball(tarball, compression):
    """Opens a compressed tarball in read-only mode as a TarFile

    This context manager transparently handles compressions unsupported
    by TarFile by using external processes.  The following compressions
    are supported "gzip", "bzip2", "xz" and "lzma".

    As the decompression may be done by an external process, seeking is
    generally not supported.
    """
    if compression == "gzip" or compression == "bzip2":
        tf = tarfile.open(tarball)
        yield tf
        tf.close()
    else:
        infd = open(tarball, "r")
        decomp = subprocess.Popen([compression, '-d'], shell=False, stdin=infd,
                                  stdout=subprocess.PIPE, universal_newlines=False)
        tobj = tarfile.open(name=tarball, mode="r|", fileobj=decomp.stdout)
        infd.close() # We don't need to keep this handle open
        yield tobj
        _close_pipeline(tobj, decomp.stdout, decomp, compression)


@contextmanager
def _open_writeable_tarfile(tarbase, compression):
    """Opens an open TarFile for the given compression

    This opens a writable TarFile and compresses it with the specified
    compression.  The compression may be done by a pipeline and thus
    the TarFile may not be seekable.

    Supported compressions are "gzip", "bzip2", "xz" and "lzma".
    """

    if compression == 'gzip' or compression == 'bzip2':
        ext = "gz"
        if compression == 'bzip2':
            ext = "bz2"
        m = "w:%s" % ext
        tarball = "%s.%s" % (tarbase, ext)
        tobj = tarfile.open(name=tarball, mode=m)
        yield tobj
        tobj.close()
        return

    if compression != "xz" and compression != "lzma":
        raise ValueError("Unknown compression %s" % compression)

    m = "w|"
    # assume compression == ext == command - holds for xz and lzma :>
    # also assume the compressor takes no arguments and writes to stdout
    tarball = "%s.%s" % (tarbase, compression)
    out = open(tarball, "w")
    compp = subprocess.Popen([compression], shell=False, stdin=subprocess.PIPE,
                             stdout=out, universal_newlines=False)
    out.close() # We don't need to keep this handle open
    tobj = tarfile.open(name=tarball, mode=m, fileobj=compp.stdin)
    yield tobj
    _close_pipeline(tobj, compp.stdin, compp, compression)



def _close_pipeline(tobj, procfd, proc, compression):
    try:
        tobj.close()
        procfd.close()
        proc.wait()
        if proc.returncode != 0:
            raise IOError("%s exited with %s" % (compression, proc.returncode))
    except:
        if proc.returncode is None:
            # something broke trouble and the process has not been reaped; kill
            # it (nicely at first)
            proc.terminate()
            proc.poll()
            if proc.returncode is None:
                proc.kill()
                proc.wait()
        # re-raise the exception
        raise