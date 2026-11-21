// Shows only what the answer carries; never sample or default data (UI polish).
import { beforeEach, describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';

import i18n from '@/i18n';
import { VisionDiagnosticLab } from '../components/canvas/VisionDiagnosticLab';

beforeEach(async () => {
  await i18n.changeLanguage('en');
});

describe('VisionDiagnosticLab', () => {
  it('invents no findings for a photo the chat did not analyse', () => {
    const file = new File(['x'], 'leaf.jpg', { type: 'image/jpeg' });
    render(<VisionDiagnosticLab image={{ file, previewUrl: 'blob:leaf' }} crop="Paddy" />);
    expect(screen.getByText('leaf.jpg')).toBeInTheDocument();
    expect(screen.getByTestId('vision-howto')).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/Stem Borer|Blight|Deficiency|%/);
  });

  it('shows a finding when one is attached', () => {
    const file = new File(['x'], 'leaf.jpg', { type: 'image/jpeg' });
    render(
      <VisionDiagnosticLab
        image={{ file, previewUrl: 'blob:leaf', diagnosisCondition: 'Leaf blast', diagnosisConfidence: 0.71 }}
      />,
    );
    expect(screen.getByText('Leaf blast')).toBeInTheDocument();
    expect(screen.getByText(/71% confidence/)).toBeInTheDocument();
  });
});
