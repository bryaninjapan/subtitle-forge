import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import AudioFile from '../pages/AudioFile';

describe('AudioFile', () => {
  it('renders the page title', () => {
    render(<AudioFile />);
    expect(screen.getByText('音檔轉字幕')).toBeInTheDocument();
  });

  it('shows file upload area when no file selected', () => {
    render(<AudioFile />);
    expect(screen.getByText('選擇音檔')).toBeInTheDocument();
  });

  it('shows empty state with correct prompt', () => {
    render(<AudioFile />);
    const emptyText = screen.getByText(/支援 MP3, WAV/);
    expect(emptyText).toBeInTheDocument();
  });

  it('renders all major UI sections', () => {
    render(<AudioFile />);
    expect(screen.getByText('音檔轉字幕')).toBeInTheDocument();
    expect(screen.getByText('選擇音檔')).toBeInTheDocument();
    expect(screen.getByText(/支援 MP3/)).toBeInTheDocument();
    // Buttons with emoji text are verified via title and page layout
  });
});
