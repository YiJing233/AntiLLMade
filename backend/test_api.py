from datetime import datetime

import storage


def _create_source(client, suffix='1'):
    payload = {
        'url': f'https://example-{suffix}.com/feed.xml',
        'title': f'Example {suffix}',
        'category': 'Tech'
    }
    response = client.post('/sources', json=payload)
    assert response.status_code == 200
    return response.json()


class TestHealth:
    def test_health_check(self, client):
        response = client.get('/health')
        assert response.status_code == 200
        assert response.json() == {'status': 'ok'}

    def test_root_endpoint(self, client):
        response = client.get('/')
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'ok'
        assert data['docs'] == '/docs'


class TestSources:
    def test_create_and_list_sources(self, client):
        source = _create_source(client, suffix='create-list')

        list_response = client.get('/sources')
        assert list_response.status_code == 200
        rows = list_response.json()
        assert any(item['id'] == source['id'] for item in rows)

    def test_source_url_uniqueness(self, client):
        payload = {
            'url': 'https://duplicate.example.com/feed.xml',
            'title': 'Duplicate Source',
            'category': 'Testing'
        }

        first = client.post('/sources', json=payload)
        second = client.post('/sources', json=payload)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()['id'] == second.json()['id']

    def test_sources_meta_reflects_unread_counts(self, client):
        source = _create_source(client, suffix='meta')
        source_id = source['id']

        inserted = storage.add_entries(
            [
                storage.Entry(
                    id=0,
                    source_id=source_id,
                    title='Entry A',
                    link='https://example.com/a',
                    published_at=datetime.fromisoformat('2026-02-12T08:00:00'),
                    summary='Summary A',
                    content='Content A',
                    unread=True
                ),
                storage.Entry(
                    id=0,
                    source_id=source_id,
                    title='Entry B',
                    link='https://example.com/b',
                    published_at=datetime.fromisoformat('2026-02-12T09:00:00'),
                    summary='Summary B',
                    content='Content B',
                    unread=False
                )
            ]
        )
        assert inserted == 2

        meta_response = client.get('/sources/meta')
        assert meta_response.status_code == 200
        meta_rows = meta_response.json()
        row = next(item for item in meta_rows if item['id'] == source_id)
        assert row['unread_count'] == 1
        assert row['has_unread'] is True
        assert row['latest_entry_at'] is not None

    def test_delete_source(self, client):
        source = _create_source(client, suffix='delete')

        delete_response = client.delete(f"/sources/{source['id']}")
        assert delete_response.status_code == 200
        assert delete_response.json() == {'status': 'deleted'}

        list_response = client.get('/sources')
        assert all(item['id'] != source['id'] for item in list_response.json())


class TestDigestAndEntries:
    def test_digest_empty_for_date(self, client):
        response = client.get('/digest?date=2026-02-12')
        assert response.status_code == 200
        payload = response.json()
        assert payload['date'] == '2026-02-12'
        assert payload['total'] == 0
        assert payload['categories'] == {}

    def test_mark_entry_read_updates_digest_and_meta(self, client):
        source = _create_source(client, suffix='mark-read')

        storage.add_entries(
            [
                storage.Entry(
                    id=0,
                    source_id=source['id'],
                    title='Unread Entry',
                    link='https://example.com/unread',
                    published_at=datetime.fromisoformat('2026-02-12T10:00:00'),
                    summary='Unread summary',
                    content='Unread content',
                    unread=True
                )
            ]
        )

        digest_before = client.get('/digest?date=2026-02-12').json()
        entry = digest_before['categories']['Tech'][0]
        assert entry['unread'] is True

        mark_response = client.post(f"/entries/{entry['id']}/read")
        assert mark_response.status_code == 200
        assert mark_response.json() == {'status': 'read'}

        digest_after = client.get('/digest?date=2026-02-12').json()
        assert digest_after['categories']['Tech'][0]['unread'] is False

        meta = client.get('/sources/meta').json()
        row = next(item for item in meta if item['id'] == source['id'])
        assert row['unread_count'] == 0
        assert row['has_unread'] is False


class TestIngest:
    def test_ingest_requires_sources(self, client):
        response = client.post('/ingest')
        assert response.status_code == 400
        assert '请先添加' in response.json()['detail']

    def test_ingest_creates_digest_entries_and_deduplicates(self, client, app_module, monkeypatch):
        _create_source(client, suffix='ingest')

        class FakeFeed:
            entries = [
                {
                    'title': 'Story 1',
                    'link': 'https://example.com/story-1',
                    'published': 'Mon, 12 Feb 2026 10:00:00 GMT',
                    'summary': 'Story 1 summary'
                },
                {
                    'title': 'Story 2',
                    'link': 'https://example.com/story-2',
                    'published': 'Mon, 12 Feb 2026 12:00:00 GMT',
                    'summary': 'Story 2 summary'
                }
            ]

        monkeypatch.setattr(app_module.feedparser, 'parse', lambda _url: FakeFeed())
        monkeypatch.setattr(app_module, 'summarize_text', lambda text: f'SUMMARY::{text[:20]}')

        first_ingest = client.post('/ingest')
        assert first_ingest.status_code == 200
        assert first_ingest.json()['inserted'] == 2

        second_ingest = client.post('/ingest')
        assert second_ingest.status_code == 200
        assert second_ingest.json()['inserted'] == 0

        digest = client.get('/digest?date=2026-02-12')
        assert digest.status_code == 200
        payload = digest.json()
        assert payload['total'] == 2
        assert 'Tech' in payload['categories']
        assert all(item['summary'].startswith('SUMMARY::') for item in payload['categories']['Tech'])


class TestStorageDatabaseOperations:
    def test_storage_add_list_and_map(self):
        source = storage.add_source(
            'https://storage.example.com/feed.xml',
            'Storage Source',
            'Ops'
        )

        sources = storage.list_sources()
        assert any(item.id == source.id for item in sources)

        source_map = storage.get_source_map()
        assert source.id in source_map
        assert source_map[source.id].title == 'Storage Source'

    def test_storage_entry_deduplication(self):
        source = storage.add_source(
            'https://storage-dedup.example.com/feed.xml',
            'Storage Dedup',
            'Ops'
        )

        entry = storage.Entry(
            id=0,
            source_id=source.id,
            title='Same Link',
            link='https://storage.example.com/shared-link',
            published_at=datetime.fromisoformat('2026-02-12T14:00:00'),
            summary='summary',
            content='content',
            unread=True
        )

        inserted_first = storage.add_entries([entry])
        inserted_second = storage.add_entries([entry])

        assert inserted_first == 1
        assert inserted_second == 0

        rows = storage.list_entries_by_date('2026-02-12')
        assert len(rows) == 1
        assert rows[0].title == 'Same Link'
