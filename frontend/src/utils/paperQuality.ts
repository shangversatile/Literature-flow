import type { Paper, ReadingPriority } from '../types'

const STRONG_RANKS = new Set(['A*', 'A'])

function score(value: number | null | undefined) {
  return typeof value === 'number' ? value : 0
}

function hasStrongRank(paper: Paper) {
  return STRONG_RANKS.has(paper.rank_value || paper.venue_rank || '')
}

export function computeReadingPriority(paper: Paper): ReadingPriority {
  const finalScore = score(paper.final_score)
  const relevance = score(paper.relevance_score)
  const authority = score(paper.authority_score)
  const frontier = score(paper.frontier_score)
  const currentYear = new Date().getFullYear()
  const isUnpublished = paper.publication_status?.toLowerCase() === 'unpublished'
  const isRecentFrontier = Boolean(paper.year && paper.year >= currentYear - 1 && frontier >= 0.45)

  if (finalScore >= 0.8) {
    return {
      label: 'Must Read',
      level: 'must-read',
      reason: 'High final score places this paper in the strongest reading tier.',
    }
  }

  if (hasStrongRank(paper) && relevance >= 0.65 && authority >= 0.6) {
    return {
      label: 'Must Read',
      level: 'must-read',
      reason: 'Strong A*/A venue signal with high relevance and authority.',
    }
  }

  if (finalScore >= 0.65) {
    return {
      label: 'High Priority',
      level: 'high',
      reason: 'Good final score makes this a strong candidate for close reading.',
    }
  }

  if (hasStrongRank(paper) && relevance >= 0.5) {
    return {
      label: 'High Priority',
      level: 'high',
      reason: 'Strong venue rank with meaningful relevance to the current topic.',
    }
  }

  if (isUnpublished && frontier >= 0.4) {
    return {
      label: 'Frontier Watch',
      level: 'frontier',
      reason: 'Unpublished or preprint-like work with a strong frontier signal.',
    }
  }

  if (isRecentFrontier) {
    return {
      label: 'Frontier Watch',
      level: 'frontier',
      reason: 'Recent paper with a frontier score high enough to monitor.',
    }
  }

  if (finalScore >= 0.45) {
    return {
      label: 'Skim',
      level: 'skim',
      reason: 'Moderate final score; skim before deciding whether to read deeply.',
    }
  }

  if (relevance >= 0.5) {
    return {
      label: 'Skim',
      level: 'skim',
      reason: 'Relevant enough to skim, but other quality signals are limited.',
    }
  }

  return {
    label: 'Archive',
    level: 'archive',
    reason: 'Low current reading signals; keep in the library for reference.',
  }
}

export function priorityBadgeClass(priority: ReadingPriority) {
  return `badge-priority-${priority.level}`
}

export function getPriorityMeaning(label: string): string {
  const meanings: Record<string, string> = {
    'Must Read': 'Read deeply and include in your core bibliography.',
    'High Priority': 'Read soon; likely useful for your research direction.',
    'Frontier Watch': 'Track as a recent or emerging paper; validate before relying on it.',
    Skim: 'Read abstract, figures, and conclusion first.',
    Archive: 'Keep as reference, but do not prioritize now.',
  }
  return meanings[label] || 'Keep as reference for now.'
}
