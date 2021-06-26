from infosystem.process.control_flow.versions import default

DEFAULT = "default"

VERSIONS = {DEFAULT: default.apply}


def apply(config, pi, variant=DEFAULT, parameters=None):
    return VERSIONS[variant](config, pi)
