import csv
import json
import os
import pytest
from engine import get_club_manager, get_stadium

def test_managers_csv_format():
	path = os.path.join('data', 'managers.csv')
	assert os.path.exists(path)

	with open(path, 'r', encoding='utf-8') as f:
		reader = csv.reader(f)
		header = next(reader)
		assert header == ['club', 'name']
		rows = list(reader)
		assert len(rows) >= 400
		for r in rows:
			assert len(r) == 2
			assert len(r[0].strip()) > 0
			assert len(r[1].strip()) > 0

def test_club_managers_json():
	path = os.path.join('data', 'club_managers.json')
	assert os.path.exists(path)

	with open(path, 'r', encoding='utf-8') as f:
		data = json.load(f)
		assert isinstance(data, dict)
		assert len(data) >= 440
		for k, v in data.items():
			assert len(k.strip()) > 0
			assert len(v.strip()) > 0

def test_stadiums_json():
	path = os.path.join('data', 'stadiums.json')
	assert os.path.exists(path)

	with open(path, 'r', encoding='utf-8') as f:
		data = json.load(f)
		assert isinstance(data, dict)
		assert len(data) >= 400
		for k, v in data.items():
			assert len(k.strip()) > 0
			assert len(v.strip()) > 0

def test_get_club_manager():
	mgr_real = get_club_manager('Real Madrid')
	assert mgr_real != 'Head Coach'
	assert 'Mourinho' in mgr_real or 'Ancelotti' in mgr_real

	mgr_city = get_club_manager('Manchester City')
	assert mgr_city != 'Head Coach'

	mgr_arsenal = get_club_manager('Arsenal')
	assert 'Arteta' in mgr_arsenal

	mgr_fallback = get_club_manager('TotallyFakeClubName123')
	assert mgr_fallback == 'TotallyFakeClubName123 Manager'

def test_get_stadium():
	stad_real = get_stadium('Real Madrid')
	assert 'Bernabéu' in stad_real or 'Bernabeu' in stad_real

	stad_city = get_stadium('Manchester City')
	assert 'Etihad' in stad_city

	stad_arsenal = get_stadium('Arsenal')
	assert 'Emirates' in stad_arsenal

	stad_fallback = get_stadium('TotallyFakeClubName123')
	assert stad_fallback == 'TotallyFakeClubName123 Ground'

