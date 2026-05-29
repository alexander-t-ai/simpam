"""Unit tests for the YAML initializer loader."""
import os
import tempfile

import pytest
import yaml

from app.initializer import InitializerLoader
from app.db.database import SessionLocal, init_db
from app.db.models import Prefix, Role


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    db = SessionLocal()
    db.query(Prefix).delete()
    db.query(Role).delete()
    db.commit()
    db.close()


@pytest.fixture
def tmp_init_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def write_yaml(directory, filename, data):
    with open(os.path.join(directory, filename), "w") as f:
        yaml.dump(data, f)


def test_load_roles(tmp_init_dir):
    write_yaml(tmp_init_dir, "prefix_vlan_roles.yml", [
        {"name": "management", "slug": "management", "description": "Mgmt network"},
        {"name": "production", "slug": "production"},
    ])

    with SessionLocal() as db:
        InitializerLoader(db, tmp_init_dir).run()
        roles = db.query(Role).order_by(Role.name).all()

    assert len(roles) == 2
    assert roles[0].name == "management"
    assert roles[0].description == "Mgmt network"
    assert roles[1].name == "production"
    assert roles[1].description is None


def test_load_roles_skips_duplicates(tmp_init_dir):
    write_yaml(tmp_init_dir, "prefix_vlan_roles.yml", [
        {"name": "management", "slug": "management"},
    ])

    with SessionLocal() as db:
        InitializerLoader(db, tmp_init_dir).run()
        InitializerLoader(db, tmp_init_dir).run()  # second run should not duplicate
        count = db.query(Role).count()

    assert count == 1


def test_load_prefixes(tmp_init_dir):
    write_yaml(tmp_init_dir, "prefix_vlan_roles.yml", [
        {"name": "infra", "slug": "infra"},
    ])
    write_yaml(tmp_init_dir, "prefixes.yml", [
        {"prefix": "10.0.0.0/8", "status": "active", "role": "infra", "description": "RFC1918"},
        {"prefix": "192.168.0.0/16", "status": "reserved"},
    ])

    with SessionLocal() as db:
        InitializerLoader(db, tmp_init_dir).run()
        prefixes = db.query(Prefix).order_by(Prefix.prefix).all()
        infra_role = db.query(Role).filter(Role.name == "infra").first()

    assert len(prefixes) == 2
    assert prefixes[0].prefix == "10.0.0.0/8"
    assert prefixes[0].status == "active"
    assert prefixes[0].role_id == infra_role.id
    assert prefixes[0].description == "RFC1918"
    assert prefixes[1].prefix == "192.168.0.0/16"
    assert prefixes[1].status == "reserved"
    assert prefixes[1].role_id is None


def test_load_prefixes_skips_duplicates(tmp_init_dir):
    write_yaml(tmp_init_dir, "prefixes.yml", [
        {"prefix": "10.0.0.0/8"},
    ])

    with SessionLocal() as db:
        InitializerLoader(db, tmp_init_dir).run()
        InitializerLoader(db, tmp_init_dir).run()
        count = db.query(Prefix).count()

    assert count == 1


def test_missing_files_are_ignored(tmp_init_dir):
    with SessionLocal() as db:
        InitializerLoader(db, tmp_init_dir).run()  # no files present — should not raise
        assert db.query(Role).count() == 0
        assert db.query(Prefix).count() == 0


def test_prefix_with_unknown_role_still_created(tmp_init_dir):
    write_yaml(tmp_init_dir, "prefixes.yml", [
        {"prefix": "172.16.0.0/12", "role": "nonexistent-role"},
    ])

    with SessionLocal() as db:
        InitializerLoader(db, tmp_init_dir).run()
        p = db.query(Prefix).first()

    assert p is not None
    assert p.prefix == "172.16.0.0/12"
    assert p.role_id is None
