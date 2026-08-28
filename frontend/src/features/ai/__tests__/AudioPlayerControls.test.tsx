import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AudioPlayerControls } from '../components/AudioPlayerControls';

describe('AudioPlayerControls', () => {
  it('renders listen button and speed selector buttons', () => {
    const handleToggle = vi.fn();
    render(
      <AudioPlayerControls
        text="Sample advisory text"
        isPlaying={false}
        onTogglePlay={handleToggle}
      />
    );

    const playBtn = screen.getByRole('button', { name: /Listen to advisory in voice/i });
    expect(playBtn).toBeInTheDocument();

    const speedBtn125 = screen.getByRole('button', { name: '1.25x' });
    expect(speedBtn125).toBeInTheDocument();

    fireEvent.click(speedBtn125);
    fireEvent.click(playBtn);

    expect(handleToggle).toHaveBeenCalledWith(1.25);
  });
});
