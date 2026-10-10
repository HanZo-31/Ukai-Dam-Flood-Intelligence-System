# Immutable official Python 3.13 base; refresh through a reviewed rebuild.
FROM python:3.13-slim-trixie@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c AS xml-library
RUN apt-get update && apt-get install -y --no-install-recommends gcc g++ make xz-utils \
    && rm -rf /var/lib/apt/lists/*
RUN python -c "import urllib.request,hashlib; data=urllib.request.urlopen('https://github.com/libexpat/libexpat/releases/download/R_2_9_0/expat-2.9.0.tar.xz',timeout=60).read(); assert hashlib.sha256(data).hexdigest() == '1e6371862cc31999b368c3b89b49994f0677e1bab5f1b2b85ae3741f5d803051'; open('/tmp/expat.tar.xz','wb').write(data)" \
    && tar -xJf /tmp/expat.tar.xz -C /tmp \
    && cd /tmp/expat-2.9.0 \
    && ./configure --prefix=/opt/expat --without-xmlwf --without-docbook \
    && make -j2 && make check && make install

# Rebuild only the matching CPython XML extension: the official interpreter
# embeds its own Expat and would otherwise keep the old parser after ldconfig.
RUN python -c "import urllib.request,hashlib; data=urllib.request.urlopen('https://www.python.org/ftp/python/3.13.16/Python-3.13.16.tar.xz',timeout=60).read(); assert hashlib.sha256(data).hexdigest() == 'f4b1bfb3c79b5bb11b8d228a12504163b4c0dab4d679828d8f5f26b6cb6ab35d'; open('/tmp/python.tar.xz','wb').write(data)" \
    && tar -xJf /tmp/python.tar.xz -C /tmp \
    && mkdir /opt/python-xml \
    && gcc -shared -fPIC -O2 -DPy_BUILD_CORE_MODULE -DXML_NS -DXML_DTD \
       $(python3-config --includes) -I/tmp/Python-3.13.16/Include/internal \
       -I/opt/expat/include /tmp/Python-3.13.16/Modules/pyexpat.c \
       -L/opt/expat/lib -Wl,-rpath,/usr/local/lib -lexpat \
       -o /opt/python-xml/pyexpat$(python3-config --extension-suffix) \
    && LD_LIBRARY_PATH=/opt/expat/lib PYTHONPATH=/opt/python-xml python -c "import pyexpat; assert pyexpat.EXPAT_VERSION == 'expat_2.9.0'" \
    && LD_LIBRARY_PATH=/opt/expat/lib PYTHONPATH=/opt/python-xml:/tmp/Python-3.13.16/Lib \
       python -m test test_pyexpat test_xml_etree test_xml_etree_c test_minidom test_sax test_xmlrpc

FROM python:3.13-slim-trixie@sha256:bf44cdfcb76cd3b41e879bc058fc37ec5872002ccfde7fcb765e218cde0cd79c AS dependencies
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt ./requirements.txt
COPY services/api/requirements-container.lock ./requirements-container.lock
COPY --from=xml-library /opt/expat/lib/libexpat.so* /usr/local/lib/
COPY --from=xml-library /opt/python-xml/pyexpat*.so /usr/local/lib/python3.13/lib-dynload/
COPY services/api/expat-sbom.cdx.json /usr/local/share/sbom/expat-sbom.cdx.json
RUN apt-get update && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends libstdc++6 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig \
    && python -c "import ctypes; library=ctypes.CDLL('libexpat.so.1'); library.XML_ExpatVersion.restype=ctypes.c_char_p; assert library.XML_ExpatVersion() == b'expat_2.9.0'" \
    && python -c "import pyexpat; assert pyexpat.EXPAT_VERSION == 'expat_2.9.0'" \
    && python -m venv /opt/venv \
    && /opt/venv/bin/python -m pip install --no-cache-dir -r requirements-container.lock \
    && /opt/venv/bin/python -m pip check
ENV PATH="/opt/venv/bin:$PATH" OBJECT_STORAGE_ROOT=/objects TMPDIR=/tmp
RUN groupadd --gid 10001 api && useradd --uid 10001 --gid api --no-create-home api \
    && mkdir /objects && chown api:api /objects

FROM dependencies AS runtime
# Installation tooling and vulnerable administrative CLI entry points are not
# part of the read-only API runtime. The verification stage retains them.
RUN python -m pip uninstall -y pip \
    && /usr/local/bin/python -m pip uninstall -y pip \
    && /usr/local/bin/python -c "import shutil; shutil.rmtree('/usr/local/lib/python3.13/ensurepip')" \
    && rm -f /usr/bin/infocmp /usr/bin/nsenter /usr/bin/mount /usr/bin/umount /usr/bin/perl* /bin/mount /bin/umount \
    && find /usr/bin /usr/sbin -type f -perm /6000 -exec chmod a-s {} +
COPY services/__init__.py ./services/__init__.py
COPY services/api/__init__.py ./services/api/__init__.py
COPY services/api/app ./services/api/app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=7s --start-period=15s --retries=3 \
    CMD ["python", "-m", "services.api.app.container_runtime", "ready"]
ENTRYPOINT ["python", "-m", "services.api.app.container_runtime"]

# Test tooling is explicitly separate from the release application layer.
FROM dependencies AS verification
USER root
COPY --from=runtime /app/services ./services
COPY services/api/requirements-dev.txt ./services/api/requirements-dev.txt
RUN python -m pip install --no-cache-dir -r services/api/requirements-dev.txt && python -m pip check
COPY database ./database
COPY scripts ./scripts
COPY tests ./tests
COPY services/api/tests ./services/api/tests
COPY services/api/Dockerfile services/api/Dockerfile.dockerignore services/api/README.md services/api/requirements-container.lock services/api/compose.yaml ./services/api/
COPY services/api/requirements-quality.txt services/api/ruff.toml services/api/mypy.ini ./services/api/
COPY docs ./docs
COPY alembic.ini pytest.ini README.md compose.yaml .env.example ./
USER 10001:10001
ENTRYPOINT ["python"]
