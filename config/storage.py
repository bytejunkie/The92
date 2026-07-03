from whitenoise.storage import CompressedManifestStaticFilesStorage


class WhiteNoiseStaticFilesStorage(CompressedManifestStaticFilesStorage):
    """WhiteNoise manifest storage that won't 500 on an unknown static path.

    ``manifest_strict = False`` makes ``{% static %}`` for a file missing from
    the manifest fall back to the raw path instead of raising at request time —
    a safety net so a stray reference degrades gracefully in production rather
    than taking a page down.
    """

    manifest_strict = False
