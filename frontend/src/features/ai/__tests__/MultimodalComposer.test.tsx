import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MultimodalComposer } from '../components/MultimodalComposer';

describe('MultimodalComposer', () => {
  it('renders text input, microphone, and image attachment buttons', () => {
    render(<MultimodalComposer onSend={vi.fn()} />);

    expect(
      screen.getByPlaceholderText(/Ask in Telugu, Hindi, or English/i)
    ).toBeInTheDocument();
    expect(screen.getByTitle(/Speak Question/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Attach Crop Image/i)).toBeInTheDocument();
  });

  it('allows language switching between Telugu, Hindi, and English', () => {
    render(<MultimodalComposer onSend={vi.fn()} />);

    const hiButton = screen.getByRole('button', { name: /HI/i });
    fireEvent.click(hiButton);

    expect(hiButton).toHaveClass('bg-primary-600');
  });

  it('triggers onSend with text query and selected language', () => {
    const handleSend = vi.fn();
    render(<MultimodalComposer onSend={handleSend} />);

    const input = screen.getByPlaceholderText(/Ask in Telugu, Hindi, or English/i);
    const sendButton = screen.getByRole('button', { name: /Send question/i });

    fireEvent.change(input, {
      target: { value: 'What is the best pesticide for stem borer in paddy?' },
    });
    fireEvent.click(sendButton);

    expect(handleSend).toHaveBeenCalledWith(
      expect.objectContaining({
        text: 'What is the best pesticide for stem borer in paddy?',
        language: 'te',
      })
    );
  });
});
