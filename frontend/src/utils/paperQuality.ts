import type { Paper, ReadingPriority } from '../types'

const STRONG_RANKS = new Set(['A*', 'Q1'])

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
  const foundation = score(paper.foundation_score)
  const implementation = score(paper.implementation_score)
  const survey = score(paper.survey_value_score)
  const frontier = score(paper.frontier_score)
  const isUnpublished = paper.publication_status?.toLowerCase() === 'unpublished'
  const citations = paper.citation_count ?? 0

  if (foundation >= 0.7) {
    return {
      label: 'Must Read',
      level: 'must-read',
      reason: 'Foundational signal is high, combining citations, rank, age, and core-method keywords.',
    }
  }

  if (finalScore >= 0.8) {
    return {
      label: 'Must Read',
      level: 'must-read',
      reason: 'High final score places this paper in the strongest reading tier.',
    }
  }

  if (hasStrongRank(paper) && citations >= 500) {
    return {
      label: 'Must Read',
      level: 'must-read',
      reason: 'Strong A*/Q1 venue signal with at least 500 citations suggests a core reference.',
    }
  }

  if (finalScore >= 0.65) {
    return {
      label: 'High Priority',
      level: 'high',
      reason: 'Good final score makes this a strong candidate for close reading.',
    }
  }

  if (implementation >= 0.6) {
    return {
      label: 'High Priority',
      level: 'high',
      reason: 'Systems implementation signal is high from implementation keywords, systems venues, citations, or PDF availability.',
    }
  }

  if (authority >= 0.7 && relevance >= 0.5) {
    return {
      label: 'High Priority',
      level: 'high',
      reason: 'High authority and meaningful relevance make this worth close reading.',
    }
  }

  if (isUnpublished && frontier >= 0.45 && citations < 100) {
    return {
      label: 'Frontier Watch',
      level: 'frontier',
      reason: 'Frontier preprint signal is high, but citations are still below 100, so monitor before relying on it.',
    }
  }

  if (relevance >= 0.45) {
    return {
      label: 'Skim',
      level: 'skim',
      reason: 'Relevant enough to skim before deciding whether it deserves deeper reading.',
    }
  }

  if (survey >= 0.45) {
    return {
      label: 'Skim',
      level: 'skim',
      reason: 'Survey, benchmark, evaluation, or dataset signal makes this useful for quick orientation.',
    }
  }

  if (finalScore >= 0.45) {
    return {
      label: 'Skim',
      level: 'skim',
      reason: 'Moderate final score; skim before deciding whether to read deeply.',
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
