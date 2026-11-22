/**
 * Submit a document to the KrishiOS assistant and follow the background job until it is done.
 *
 * The server reads the document (it is not stored) and the summary takes a few minutes, so the
 * job is checked every few seconds. Polling stops when the component unmounts.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import {
  assistantApi,
  type AnalyzeOptions,
  type DocumentAnalysisResult,
} from '@/services/api/assistant';

export type DocPhase = 'idle' | 'queued' | 'working' | 'done' | 'failed';

const POLL_MS = 3000;
const MAX_POLLS = 400; // 20 minutes

export function useDocumentAnalysis() {
  const [phase, setPhase] = useState<DocPhase>('idle');
  const [ahead, setAhead] = useState(0);
  const [result, setResult] = useState<DocumentAnalysisResult | null>(null);
  const cancelled = useRef(false);

  useEffect(() => {
    cancelled.current = false;
    return () => {
      cancelled.current = true;
    };
  }, []);

  const reset = useCallback(() => {
    setPhase('idle');
    setResult(null);
  }, []);

  const analyze = useCallback(async (file: File, opts: AnalyzeOptions) => {
    setResult(null);
    setPhase('queued');
    try {
      let job = await assistantApi.analyzeDocument(file, opts);
      for (let i = 0; i < MAX_POLLS && !cancelled.current; i += 1) {
        if (job.status === 'done' || job.status === 'failed') break;
        setPhase(job.status === 'running' ? 'working' : 'queued');
        setAhead(job.queue_position);
        await new Promise((resolve) => setTimeout(resolve, POLL_MS));
        job = await assistantApi.getDocumentJob(job.job_id);
      }
      if (cancelled.current) return;
      if (job.status === 'done' && job.result) {
        setResult(job.result);
        setPhase('done');
      } else {
        setPhase('failed');
      }
    } catch (error) {
      console.error('Document analysis failed:', error);
      if (!cancelled.current) setPhase('failed');
    }
  }, []);

  return { phase, ahead, result, analyze, reset, busy: phase === 'queued' || phase === 'working' };
}
