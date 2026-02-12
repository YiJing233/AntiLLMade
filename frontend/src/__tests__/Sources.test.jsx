import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Sources from '../pages/Sources.jsx';

describe('Sources page', () => {
  const sourceMeta = [
    {
      id: 10,
      title: 'Playwright Blog',
      url: 'https://playwright.dev/rss.xml',
      category: 'Testing',
      unread_count: 3,
      has_unread: true,
      latest_entry_at: '2026-02-12T01:00:00'
    }
  ];

  const defaultProps = {
    totalUnread: 3,
    sourceMeta,
    form: { title: '', url: '', category: '默认' },
    setForm: vi.fn(),
    onCreateSource: vi.fn((event) => event.preventDefault()),
    onRemoveSource: vi.fn(),
    onRefreshSourceMeta: vi.fn(),
    onSeedSources: vi.fn(),
    error: ''
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows CRUD view and handles actions', async () => {
    const user = userEvent.setup();
    render(<Sources {...defaultProps} />);

    expect(screen.getByText('未读汇总：3 条')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '添加订阅源' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: '刷新订阅' }));
    expect(defaultProps.onRefreshSourceMeta).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: '一键填充示例源' }));
    expect(defaultProps.onSeedSources).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole('button', { name: '移除' }));
    expect(defaultProps.onRemoveSource).toHaveBeenCalledWith(10);
  });

  it('switches to raw view and back to CRUD view', async () => {
    const user = userEvent.setup();
    render(<Sources {...defaultProps} />);

    await user.click(screen.getByRole('button', { name: 'Raw 视图' }));
    expect(screen.getByText(/playwright\.dev\/rss\.xml/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'CRUD 视图' }));
    expect(screen.getByRole('button', { name: '添加订阅源' })).toBeInTheDocument();
  });
});
