from dtwin.digitaltwin.ocpn.discovery.versions import inductive_and_tr

INDUCTIVE_AND_TR = "inductive_and_tr"

VERSIONS = {INDUCTIVE_AND_TR: inductive_and_tr.apply}

def apply(df, variant=INDUCTIVE_AND_TR, parameters=None):
    return VERSIONS[variant](df, parameters=parameters)
