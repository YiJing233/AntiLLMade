import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../App.jsx';

function jsonResponse(payload, ok = true, status = 200) {
  return Promise.resolve({
    ok,
    status,
    json: async () => payload
  });
}

describe('App', () => {
  beforeEach(() => {
    window.history.pushState({}, '', '/');
    global.fetch = vi.fn((input, init) => {
      const url = String(input);
      if (url.includes('/sources/meta')) {
        return jsonResponse([
          {
            id: 1,
            url: 'https://example.com/feed.xml',
            title: 'Example Feed',
            category: 'Tech',
            unread_count: 2,
            has_unread: true,
            latest_entry_at: null
          }
        ]);
      }
      if (url.includes('/digest')) {
        return jsonResponse({ date: '2026-02-12', total: 0, categories: {} });
      }
      if (url.includes('/sources') && init?.method === 'POST') {
        return jsonResponse({ id: 2 });
      }
      return jsonResponse({ status: 'ok' });
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('renders Sources by default and navigates to Digest', async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByRole('heading', { name: '订阅源管理' })).toBeInTheDocument();
    expect(screen.getByText('未读汇总：2 条')).toBeInTheDocument();

    await user.click(screen.getByRole('link', { name: 'Digest' }));
    expect(await screen.findByRole('heading', { name: '长上下文资讯阅读站' })).toBeInTheDocument();
  });

  it('submits source form and calls source creation endpoint', async () => {
    const user = userEvent.setup();
    render(<App />);

    await screen.findByRole('heading', { name: '订阅源管理' });

    await user.type(screen.getByPlaceholderText('订阅源名称'), 'New Source');
    await user.type(screen.getByPlaceholderText('订阅源链接'), 'https://new.example.com/feed.xml');
    await user.type(screen.getByPlaceholderText('分类'), 'News');
    await user.click(screen.getByRole('button', { name: '添加订阅源' }));

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('/sources'),
        expect.objectContaining({ method: 'POST' })
      );
    });
  });
});
