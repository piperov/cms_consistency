from __future__ import print_function
import json, re, getopt, os
import sys, uuid

from config import Config
from partition import part

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.oracle import RAW
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.dialects.oracle import RAW, CLOB
from sqlalchemy.dialects.mysql import BINARY
from sqlalchemy.types import TypeDecorator, CHAR, String

#from sqlalchemy import schema

Usage = """
python db_dump.py [-a] [-l] [-o<output file>] [-r <path>] -c <config.yaml> <rse_name>
    -o <prefix> -- output file prefix
    -c <config file> -- required
    -a -- include all replicas, otherwise active only (state='A')
    -l -- include more columns, otherwise physical path only, automatically on if -a is used
"""


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses PostgreSQL's UUID type,
    uses Oracle's RAW type,
    uses MySQL's BINARY type,
    otherwise uses CHAR(32), storing as stringified hex values.

    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        elif dialect.name == 'oracle':
            return dialect.type_descriptor(RAW(16))
        elif dialect.name == 'mysql':
            return dialect.type_descriptor(BINARY(16))
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value).lower()
        elif dialect.name == 'oracle':
            return uuid.UUID(value).bytes
        elif dialect.name == 'mysql':
            return uuid.UUID(value).bytes
        else:
            if not isinstance(value, uuid.UUID):
                return "%.32x" % uuid.UUID(value)
            else:
                # hexstring
                return "%.32x" % value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'oracle':
            return str(uuid.UUID(bytes=value)).replace('-', '').lower()
        elif dialect.name == 'mysql':
            return str(uuid.UUID(bytes=value)).replace('-', '').lower()
        else:
            return str(uuid.UUID(value)).replace('-', '').lower()

opts, args = getopt.getopt(sys.argv[1:], "o:c:la")
opts = dict(opts)

all_replicas = "-a" in opts
long_output = "-l" in opts or all_replicas
out_prefix = opts.get("-o")
if not args or not "-c" in opts:
	print (Usage)
	sys.exit(2)

rse_name = args[0]

config = Config(opts["-c"])

Base = declarative_base()
Base.metadata.schema = config.DBSchema

class Replica(Base):
	__tablename__ = "replicas"
	path = Column(String)
	state = Column(String)
	rse_id = Column(GUID(), primary_key=True)
	scope = Column(String, primary_key=True)
	name = Column(String, primary_key=True)

class RSE(Base):
        __tablename__ = "rses"
        id = Column(GUID(), primary_key=True)
        rse = Column(String)

nparts = config.nparts(rse_name) or 1

if nparts > 1:
	if out_prefix is None:
		print("Output file path must be specified if partitioning is requested")
		sys.exit(1)

outputs = [sys.stdout]
if out_prefix is not None:
	outputs = [open("%s.%05d" % (out_prefix, i), "w") for i in range(nparts)]

subdir = config.path_root(rse_name) or "/"
if not subdir.endswith("/"):	subdir = subdir + "/"

engine = create_engine(config.DBURL,  echo=True)
Session = sessionmaker(bind=engine)
session = Session()

rse = session.query(RSE).filter(RSE.rse == rse_name).first()
if rse is None:
	print ("RSE %s not found" % (rse_name,))
	sys.exit(1)

rse_id = rse.id

print ("rse_id:", type(rse_id), rse_id)

rules = config.lfn_to_path(rse_name)

batch = 100000

if all_replicas:
	replicas = session.query(Replica).filter(Replica.rse_id==rse_id).yield_per(batch)
else:
	replicas = session.query(Replica)	\
		.filter(Replica.rse_id==rse_id)	\
		.filter(Replica.state=='A')	\
		.yield_per(batch)
n = 0
for r in replicas:
		path = r.path
		if not path:
			for rule in rules:
				match = rule["path"]
				rewrite = rule["out"]
				if match.match(r.name):
					path = match.sub(rewrite, r.name)
					break

		if not path.startswith(subdir):
			continue

		ipart = part(nparts, path)
		out = outputs[ipart]

		if long_output:
			out.write("%s\t%s\t%s\t%s\t%s\n" % (rse_name, r.scope, r.name, path or "null", r.state))
		else:
			out.write("%s\n" % (path or "null", ))
		n += 1
		if n % batch == 0:
			print(n)
print(n)
[out.close() for out in outputs]

