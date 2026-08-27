import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StageThinkingIndicator } from '../components/StageThinkingIndicator';
import type { StageInfo } from '../types/conversation';

const mockStage: StageInfo = {
  stage: 'analyzing_image',
  message: 'Analyzing crop image with computer vision...',
  detail: 'Checking leaf symptoms and disease markers',
  stepNumber: 1,
  totalSteps: 3,
};

describe('StageThinkingIndicator', () => {
  it('renders stage message, step count, and detail', () => {
    render(<StageThinkingIndicator stageInfo={mockStage} />);

    expect(screen.getByText('Analyzing crop image with computer vision...')).toBeInTheDocument();
    expect(screen.getByText('Step 1 of 3')).toBeInTheDocument();
    expect(screen.getByText('Checking leaf symptoms and disease markers')).toBeInTheDocument();
  });
});
