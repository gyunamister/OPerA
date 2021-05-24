import json
import sqlite3
import time
from datetime import datetime
from dtwin.infosystem.database.configure import con_key, con_sec, a_token, a_secret
import pandas as pd

from simulate import Simulator


def create_table(conn, cur):
    cur.execute("DROP TABLE IF EXISTS events")
    conn.commit()
    # cur.execute("CREATE TABLE events(event_id TEXT, event_activity TEXT, event_timestamp TEXT, order TEXT, event_income REAL, event_costs REAL, event_profit REAL, package TEXT, delivery TEXT, event_add_fee REAL)")
    # conn.commit()


# create_table()

# while True:
#     try:
#         auth = OAuthHandler(con_key, con_sec)
#         auth.set_access_token(a_token, a_secret)
#         twitterStream = tweepy.Stream(auth, WineListener())
#         twitterStream.filter(track=['wine'])
#     except Exception as e:
#         print(str(e))
#         time.sleep(4)


def pour_events(engine, conn):
    batch_size = 5
    total_size = 5*5
    batch_df = pd.DataFrame()
    for i in range(total_size):
        engine.order_id = i*2
        engine.timestamp = datetime.timestamp(datetime.now())
        case_df = engine.generate_case()
        if i == 0:
            batch_df = case_df
        else:
            batch_df = batch_df.append(case_df)
            if i % batch_size == 0:
                batch_df.to_sql('events', con=conn, if_exists='append')
                # print("events appended: {}".format(batch_df))
                # batch_df.to_csv("./test{}.csv".format(i/batch_size))
                batch_df = pd.DataFrame()
        time.sleep(1)


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


if __name__ == '__main__':
    limit = 200
    conn = sqlite3.connect(r"./eventstream.sqlite")
    cur = conn.cursor()
    create_table(conn, cur)
    engine = Simulator()
    pour_events(engine, conn)
    df = analyze_events(conn, cur, limit)
    # print(df)
    # delete_events(conn, cur, limit)
    # df2 = analyze_events(conn, cur, 1000)
    # print(df2)
