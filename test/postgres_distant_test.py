#!/usr/bin/env python2
from __future__ import absolute_import
import sys
sys.path.insert(0, '..')

from versioningDB import versioning 
from pyspatialite import dbapi2
import psycopg2
import os
import tempfile


def prtTab( cur, tab ):
    print ("--- ",tab," ---")
    cur.execute("SELECT ogc_fid, trunk_rev_begin, trunk_rev_end, trunk_parent, trunk_child, length FROM "+tab)
    for r in cur.fetchall():
        t = []
        for i in r: t.append(str(i))
        print ('\t| '.join(t))

def prtHid( cur, tab ):
    print ("--- ",tab," ---")
    cur.execute("SELECT ogc_fid FROM "+tab)
    for [r] in cur.fetchall(): print (r)

def test(host, pguser):
    pg_conn_info = "dbname=epanet_test_db host=" + host + " user=" + pguser
    pg_conn_info_cpy = "dbname=epanet_test_copy_db host=" + host + " user=" + pguser
    test_data_dir = os.path.dirname(os.path.realpath(__file__))
    tmp_dir = tempfile.gettempdir()

    # create the test database

    os.system("dropdb --if-exists -h " + host + " -U "+pguser+" epanet_test_db")
    os.system("dropdb --if-exists -h " + host + " -U "+pguser+" epanet_test_copy_db")
    os.system("createdb -h " + host + " -U "+pguser+" epanet_test_db")
    os.system("createdb -h " + host + " -U "+pguser+" epanet_test_copy_db")
    os.system("psql -h " + host + " -U "+pguser+" epanet_test_db -c 'CREATE EXTENSION postgis'")
    os.system("psql -h " + host + " -U "+pguser+" epanet_test_copy_db -c 'CREATE EXTENSION postgis'")
    os.system("psql -h " + host + " -U "+pguser+" epanet_test_db -f "+test_data_dir+"/epanet_test_db.sql")

    # chechout
    #tables = ['epanet_trunk_rev_head.junctions','epanet_trunk_rev_head.pipes']
    tables = ['epanet_trunk_rev_head.junctions', 'epanet_trunk_rev_head.pipes']
    pgversioning = versioning.pgLocal(pg_conn_info, 'epanet_trunk_rev_head', pg_conn_info_cpy)
    pgversioning.checkout(tables)
    
    
    pcurcpy = versioning.Db(psycopg2.connect(pg_conn_info_cpy))
    pcur = versioning.Db(psycopg2.connect(pg_conn_info))


    pcurcpy.execute("INSERT INTO epanet_trunk_rev_head.pipes_view(id, start_node, end_node, wkb_geometry) VALUES ('2','1','2',ST_GeometryFromText('LINESTRING(1 1,0 1)',2154))")
    pcurcpy.execute("INSERT INTO epanet_trunk_rev_head.pipes_view(id, start_node, end_node, wkb_geometry) VALUES ('3','1','2',ST_GeometryFromText('LINESTRING(1 -1,0 1)',2154))")
    pcurcpy.commit()


    prtHid(pcurcpy, 'epanet_trunk_rev_head.pipes_view')

    pcurcpy.execute("SELECT * FROM epanet_trunk_rev_head.pipes_view")
    assert( len(pcurcpy.fetchall()) == 3 )
    pcur.execute("SELECT * FROM epanet.pipes")
    assert( len(pcur.fetchall()) == 1 )
    pgversioning.commit('commit')

    sqlite_test_filename1 = os.path.join(tmp_dir, "versioning_base_test1.sqlite")
    if os.path.isfile(sqlite_test_filename1): os.remove(sqlite_test_filename1)
    spversioning1 = versioning.spatialite(sqlite_test_filename1, pg_conn_info)
    spversioning1.checkout( ['epanet_trunk_rev_head.pipes','epanet_trunk_rev_head.junctions'] )
    scon = dbapi2.connect(sqlite_test_filename1)
    scur = scon.cursor()
    scur.execute("INSERT INTO pipes_view(id, start_node, end_node, GEOMETRY) VALUES ('4', '10','100',GeomFromText('LINESTRING(2 0, 0 2)',2154))")
    scon.commit()
    spversioning1.commit("sp commit")
    
    pgversioning.update( )
    
    pcurcpy.close()
    pcur.close()
    
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python2 versioning_base_test.py host pguser")
    else:
        test(*sys.argv[1:])