import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Digest from '../pages/Digest.jsx';

describe('Digest page', () => {
  const baseProps = {
    date: '2026-02-12',
    setDate: vi.fn(),
    digest: { date: '2026-02-12', total: 1 },
    categories: [],
    loading: false,
    error: '',
    onRefreshDigest: vi.fn(),
    onIngestNow: vi.fn(),
    onMarkRead: vi.fn()
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows empty digest state when no categories are available', () => {
    render(<Digest {...baseProps} categories={[]} />);
    expect(screen.getByText('暂无日报内容。')).toBeInTheDocument();
  });

  it('renders digest cards and marks entries as read', async () => {
    const user = userEvent.setup();
    render(
      <Digest
        {...baseProps}
        categories={[
          [
            'Testing',
            [
              {
                id: 77,
                title: 'Release Notes',
                link: 'https://example.com/release-notes',
                published_at: '2026-02-12T10:00:00',
                source_title: 'Example Feed',
                summary: 'Summary text',
                content: 'Detailed content',
                unread: true
              }
            ]
          ]
        ]}
      />
    );

    expect(screen.getByRole('heading', { name: 'Release Notes' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '标记已读' }));
    expect(baseProps.onMarkRead).toHaveBeenCalledWith(77);
  });

  it('fires refresh, ingest, and date change callbacks', async () => {
    const user = userEvent.setup();
    render(<Digest {...baseProps} />);

    await user.click(screen.getByRole('button', { name: '刷新日报' }));
    await user.click(screen.getByRole('button', { name: '立即拉取' }));
    await user.type(screen.getByLabelText('日报日期'), '2026-02-13');

    expect(baseProps.onRefreshDigest).toHaveBeenCalledTimes(1);
    expect(baseProps.onIngestNow).toHaveBeenCalledTimes(1);
    expect(baseProps.setDate).toHaveBeenCalled();
  });
});
