from dtween.digitaltwin.digitaltwin.operation.versions import projection

import pandas as pd


PROJECTION = "projection"

VERSIONS = {
    PROJECTION: projection.apply
}


def apply(ocpn, log, marking, variant=PROJECTION, parameters=None):
    return VERSIONS[variant](ocpn, log=log, marking=marking, parameters=parameters)


def analyze_events(conn, cur, limit):
    query = "SELECT * FROM events ORDER BY event_timestamp ASC LIMIT {}".format(
        limit)
    # cur.execute("SELECT * FROM events ORDER BY event_timestamp ASC")
    # rows = cur.fetchall()

    # for row in rows:
    #     print(row)

    df = pd.read_sql_query(query, conn)
    del df['index']
    return df


def delete_events(conn, cur, limit):
    sql = "DELETE FROM events WHERE event_id IN(SELECT event_id FROM events ORDER BY event_timestamp ASC LIMIT {})".format(
        limit)
    cur.execute(sql)
    conn.commit()
