export const ROLE_OPTIONS = [
  'Actor',
  'Director',
  'Producer',
  'Line Producer',
  'Cinematographer',
  'Camera Operator',
  'Focus Puller',
  'Gaffer',
  'Light Boy / Electrician',
  'Grip',
  'Editor',
  'Colorist',
  'VFX Artist',
  'Sound Recordist',
  'Sound Designer',
  'Music Director',
  'Screenwriter',
  'Assistant Director',
  'Production Manager',
  'Production Designer',
  'Art Director',
  'Costume Designer',
  'Makeup Artist',
  'Choreographer',
  'Stunt Coordinator',
  'Casting Director',
  'Location Manager',
] as const

export type Role = (typeof ROLE_OPTIONS)[number]

export const PROJECT_TYPES = [
  'Feature Film',
  'Short Film',
  'Web Series',
  'TV Series',
  'Documentary',
  'Advertisement',
  'Music Video',
] as const

export type ProjectType = (typeof PROJECT_TYPES)[number]
