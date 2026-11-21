export type PlanId = 'free' | 'pro' | 'ultra';

export interface PlanFeature {
  text: string;
  isExclusive?: boolean;
  tooltip?: string;
}

export interface SubscriptionPlan {
  id: PlanId;
  name: string;
  badge: string;
  badgeColor: 'secondary' | 'success' | 'discovery';
  tagline: string;
  description: string;
  priceINR: number;
  priceUSD: number;
  usdApproxText: string;
  priceMonthly: number; // Backward-compatibility alias to priceINR
  priceAnnual: number;
  ribbonLabel?: string;
  isPopular?: boolean;
  isUltra?: boolean;
  ctaText: string;
  features: PlanFeature[];
}

export interface ComparisonRow {
  category: string;
  feature: string;
  free: string | boolean;
  pro: string | boolean;
  ultra: string | boolean;
  isUltraExclusive?: boolean;
  description?: string;
}

export const PRICING_CONFIG = {
  inrSymbol: '₹',
  usdSymbol: '$',
  inrCode: 'INR',
  usdCode: 'USD',
  billingNote: 'USD prices are approximate and may vary with exchange rates.',
  billingCycleDefault: 'monthly' as const,
  allowAnnualBilling: false, // Ready for annual billing to be enabled later
};

/**
 * Format a number using Indian Numbering System (e.g. 399 -> 399, 10000 -> 10,000)
 */
export const formatPriceINR = (amount: number): string => {
  return new Intl.NumberFormat('en-IN').format(amount);
};

/**
 * Format USD amount to 2 decimal places or integer if 0
 */
export const formatPriceUSD = (amount: number): string => {
  return amount === 0 ? '0' : amount.toFixed(2);
};

export const SUBSCRIPTION_PLANS: Record<PlanId, SubscriptionPlan> = {
  free: {
    id: 'free',
    name: 'Free',
    badge: 'FREE',
    badgeColor: 'secondary',
    tagline: 'For writers beginning their investigation.',
    description: 'No payment required. Basic writing and limited AI features for early case files.',
    priceINR: 0,
    priceUSD: 0,
    usdApproxText: '$0 USD',
    priceMonthly: 0,
    priceAnnual: 0,
    ctaText: 'Get Started',
    features: [
      { text: 'Basic story creation' },
      { text: 'Basic chapter writing' },
      { text: 'Limited AI Co-Writer usage (15 assists/day)' },
      { text: 'Limited Universe Memory (10 lore memories)' },
      { text: 'Basic character and story management (up to 8 dossiers)' },
      { text: 'Access to the standard writing workspace & typewriter soundscape' }
    ]
  },
  pro: {
    id: 'pro',
    name: 'Pro',
    badge: 'PRO',
    badgeColor: 'success',
    tagline: 'For writers building complex fictional universes.',
    description: 'Enhanced narrative intelligence with expanded vector memory and multi-chapter continuity auditing.',
    priceINR: 399,
    priceUSD: 4.50,
    usdApproxText: 'approximately $4.50 USD',
    priceMonthly: 399,
    priceAnnual: 319,
    isPopular: true,
    ribbonLabel: 'MOST POPULAR',
    ctaText: 'Upgrade to Pro',
    features: [
      { text: 'Everything included in Free' },
      { text: 'Increased AI Co-Writer usage (150 assists/day)' },
      { text: 'Increased Universe Memory capacity (100 lore codices)' },
      { text: 'Expanded AI-assisted story analysis & plot contradiction radar' },
      { text: 'Greater capacity for character profiles & story lore (50 dossiers)' },
      { text: 'Improved access to story continuity and persistent memory features' },
      { text: 'High-speed generative AI processing lane' }
    ]
  },
  ultra: {
    id: 'ultra',
    name: 'Ultra',
    badge: 'ULTRA',
    badgeColor: 'discovery',
    tagline: 'For writers creating expansive cinematic universes.',
    description: 'The pinnacle membership. Maximum memory, unrestricted AI co-writing, and living Story Animation.',
    priceINR: 799,
    priceUSD: 9.00,
    usdApproxText: 'approximately $9.00 USD',
    priceMonthly: 799,
    priceAnnual: 639,
    isUltra: true,
    ribbonLabel: 'ANIMATION INCLUDED',
    ctaText: 'Unlock Ultra',
    features: [
      { text: 'Everything included in Pro' },
      { text: 'Highest AI Co-Writer usage allowance (unrestricted prose assistance)' },
      { text: 'Maximum Universe Memory capacity (infinite vector lore chunks)' },
      { text: 'Expanded AI story analysis allowance & instant plot hole triage' },
      { text: 'Greater capacity for large fictional universes (unlimited dossiers)' },
      { 
        text: 'Story Animation — Exclusive Ultra Feature', 
        isExclusive: true,
        tooltip: 'Transform your written manuscripts into atmospheric cinematic animatics with AI scene direction.' 
      },
      { text: 'Access to all available premium writing and memory capabilities' },
      { text: 'Bespoke narrative tone calibration & manuscript export studio' }
    ]
  }
};

export const COMPARISON_TABLE: ComparisonRow[] = [
  {
    category: 'Core Studio',
    feature: 'Story Creation',
    free: 'Included',
    pro: 'Included',
    ultra: 'Included',
    description: 'Architecting universes, case files, and overarching premise logs.'
  },
  {
    category: 'Core Studio',
    feature: 'Chapter Writing',
    free: 'Included',
    pro: 'Included',
    ultra: 'Included',
    description: 'Distraction-free typewriter manuscript view with tactile page-turning.'
  },
  {
    category: 'AI Intelligence',
    feature: 'AI Co-Writer Usage',
    free: 'Limited',
    pro: 'Increased',
    ultra: 'Highest',
    description: 'Context-grounded narrative continuation, dialogue sharpening, and sensory expansion.'
  },
  {
    category: 'AI Intelligence',
    feature: 'Universe Memory',
    free: 'Limited',
    pro: 'Increased',
    ultra: 'Maximum',
    description: 'RAG semantic vector memory across manuscript chunks, lore, and world laws.'
  },
  {
    category: 'Universe Architecture',
    feature: 'Character Management',
    free: 'Included',
    pro: 'Included',
    ultra: 'Included',
    description: 'Dossier archives, Person of Interest classification, and auto-syncing.'
  },
  {
    category: 'Universe Architecture',
    feature: 'Story Continuity',
    free: 'Basic',
    pro: 'Expanded',
    ultra: 'Expanded',
    description: 'Cross-chapter contradiction auditing and chronological timeline tracking.'
  },
  {
    category: 'AI Intelligence',
    feature: 'AI Story Analysis',
    free: 'Limited',
    pro: 'Increased',
    ultra: 'Highest',
    description: 'Plot hole diagnosis, pacing radar, and timeline anomaly resolution.'
  },
  {
    category: 'Cinematic Creation',
    feature: 'Story Animation',
    free: 'Locked',
    pro: 'Locked',
    ultra: 'Exclusive',
    isUltraExclusive: true,
    description: 'Transform written prose into animated cinematic scene reels with dynamic character staging.'
  }
];

export const MOCK_SUBSCRIPTION_LIMITS = {
  free: {
    aiDailyLimit: 15,
    memoryLimit: 10,
    characterLimit: 8,
    storyLimit: 2,
    hasStoryAnimation: false
  },
  pro: {
    aiDailyLimit: 150,
    memoryLimit: 100,
    characterLimit: 50,
    storyLimit: 15,
    hasStoryAnimation: false
  },
  ultra: {
    aiDailyLimit: 'Unlimited',
    memoryLimit: 'Infinite',
    characterLimit: 'Unlimited',
    storyLimit: 'Unlimited',
    hasStoryAnimation: true
  }
};
