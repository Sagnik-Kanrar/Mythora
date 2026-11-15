import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  BookOpen, 
  Compass, 
  Feather, 
  Users, 
  GitBranch, 
  Brain, 
  AlertTriangle, 
  Settings, 
  ChevronLeft, 
  ChevronRight, 
  X,
  Sparkles,
  CheckCircle2
} from 'lucide-react';
import { sound } from '../../services/audioService';

interface ManualSection {
  id: string;
  chapterNumber: string;
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  quote: string;
  overview: string;
  features: string[];
  tips: string;
}

const manualSections: ManualSection[] = [
  {
    id: 'home',
    chapterNumber: 'Chapter I',
    title: 'The Sanctum & Desk',
    subtitle: 'Command Center for the Investigative Novelist',
    icon: Compass,
    quote: '"Order at the desk begets clarity in the manuscript." — Victorian Detective Maxim',
    overview: 'The Desk serves as your personal authorial study. It brings together your active manuscripts, word count telemetry, chapter milestones, and recent investigation dossiers into an ambient Victorian workspace.',
    features: [
      'Active Manuscript Dossier: Quick access to your current writing project with instant word counts and progress bars.',
      'Investigative Quick Stats: Real-time overview of characters profiled, clue connections established, and plot nodes mapped.',
      'Recent Dossiers & Clues: Fast navigation into recently edited scenes, character profiles, and suspect boards.',
      'Atmospheric Ambience: Responsive soundscapes and visual parchment cues designed for sustained focus.'
    ],
    tips: 'Use the Desk at the start of every writing session to review your story roadmap before diving into the Writing Studio.'
  },
  {
    id: 'studio',
    chapterNumber: 'Chapter II',
    title: 'The Writing Studio',
    subtitle: 'Distraction-Free Manuscript & Fountain Pen Environment',
    icon: Feather,
    quote: '"Words etched onto parchment hold the power to summon ghosts and expose truths."',
    overview: 'The Writing Studio is the beating heart of Mythora. Crafted to replicate an antique typewriter and illuminated parchment manuscript, it blends tactile typography with state-of-the-art narrative intelligence.',
    features: [
      'Parchment & Typewriter Aesthetics: Realistic page texture, custom serif typography, and tactile auditory feedback.',
      'Chapter & Scene Hierarchy: Effortlessly organize acts, chapters, and individual pages with drag-and-drop ease.',
      'Real-Time Pacing Monitor: Built-in sensory rhythm tracker that alerts you when scenes require more tension, dialogue, or atmospheric detail.',
      'AI Prose Co-Writer: Sensory-rich descriptive expansion, dialogue sharpening, and tone calibration rooted exclusively in your story lore.'
    ],
    tips: 'Toggle ambient sound effects (Rain on Cobblestones or Fireplace) in the audio settings to immerse yourself fully in your scene.'
  },
  {
    id: 'investigation',
    chapterNumber: 'Chapter III',
    title: 'Investigation Board & Dossier AI',
    subtitle: 'Victorian Corkboard & Evidence Threading',
    icon: Users,
    quote: '"Follow the red thread; it never lies even when the suspects do."',
    overview: 'The Investigation Board is an interactive detective corkboard that visualizes the hidden web of connections between your characters, crimes, and story events. Powered by Dossier AI, it analyzes your actual manuscript to weave red thread connections.',
    features: [
      'Intelligent Red Threading: AI inspects your saved story chapters and connects characters based strictly on genuine relationships and story evidence.',
      'Dual Character & Clue Cards: Moveable, draggable polaroids and evidence notes pinned with antique brass tacks.',
      'Hover-Based Relationship Inspection: Hover over any character card to highlight their active connections and inspect relationship summaries.',
      'Dynamic Board Auto-Zoom: The board intelligently auto-zooms and balances spacing based on how many characters inhabit your story world.'
    ],
    tips: 'Click "AI Thread Story" whenever you add a new chapter to discover newly formed alliances, rivalries, and hidden betrayals.'
  },
  {
    id: 'characters',
    chapterNumber: 'Chapter IV',
    title: 'Character Dossiers & Archives',
    subtitle: 'Comprehensive Psychological & Biographical Profiles',
    icon: Users,
    quote: '"Every soul harbors a secret; the writer\'s duty is to extract it."',
    overview: 'Character Dossiers house detailed archival folders for every protagonist, antagonist, witness, and suspect in your story universe.',
    features: [
      'Deep Archetype Profiling: Record psychological traits, moral alignments, secret motives, flaws, and distinctive speech patterns.',
      'Physical Descriptions & Artifacts: Document identifying scars, heirlooms, attire, and personal belongings.',
      'Dynamic Relationship Matrix: Cross-reference how each character perceives others across the narrative arc.',
      'Timeline Placement: Link characters directly to events and scenes they participate in.'
    ],
    tips: 'Fill out the "Hidden Motive" field early. The AI will weave subtle foreshadowing into prose suggestions based on these secrets.'
  },
  {
    id: 'architect',
    chapterNumber: 'Chapter V',
    title: 'Story Architect & Outlining',
    subtitle: 'Narrative Engineering & Structural Plotting',
    icon: GitBranch,
    quote: '"Structure is the architecture upon which the mystery rests."',
    overview: 'The Story Architect provides structural blueprints for plotting complex mysteries, gothic adventures, and multi-threaded novels using established storytelling paradigms.',
    features: [
      'Three-Act & Mystery Beat Sheets: Pre-built templates for murder mysteries, thrillers, psychological gothic tales, and classic epics.',
      'Tension & Pacing Curves: Visualize the dramatic stakes and emotional rhythm across each chapter.',
      'Beat-by-Beat Outlining: Break complex plots down into manageable narrative checkpoints.',
      'Foreshadowing Tracker: Keep track of clues planted in Act I that pay off in Act III.'
    ],
    tips: 'Use the Architect to outline your climactic twist before writing Act II so all clues logically point toward the revelation.'
  },
  {
    id: 'memory',
    chapterNumber: 'Chapter VI',
    title: 'Universe Memory & Lore Codex',
    subtitle: 'Persistent Worldbuilding Knowledge Base',
    icon: Brain,
    quote: '"A universe without laws collapses under its own weight."',
    overview: 'The Universe Memory is a vector-powered lore repository that records rules of magic, technology, historical events, factions, and geographical lore across your world.',
    features: [
      'Persistent World Facts: Store immutable laws of your setting that the AI must never contradict.',
      'Faction & Location Directories: Catalog noble houses, secret societies, haunted lighthouses, and subterranean vaults.',
      'Contextual AI Retrieval: The AI automatically injects relevant lore into your writing studio suggestions when relevant terms appear.',
      'Chronological Timeline: Ensure events, wars, and discoveries remain chronologically sound.'
    ],
    tips: 'Add specific sensory details to your location codex entries (e.g., "smell of brine and wet coal") to make AI descriptions feel grounded.'
  },
  {
    id: 'plotholes',
    chapterNumber: 'Chapter VII',
    title: 'Plot Hole & Logic Detector',
    subtitle: 'Forensic Manuscript Auditor',
    icon: AlertTriangle,
    quote: '"Truth withstands scrutiny; falsehood falters under inspection."',
    overview: 'The Plot Hole Detector performs rigorous forensic audits on your manuscript, identifying timeline inconsistencies, character whereabouts anomalies, and abandoned narrative threads.',
    features: [
      'Timeline Contradiction Alerts: Flags impossible character travel times or overlapping alibis.',
      'Abandoned Clue Warning: Identifies Chekhov\'s guns introduced early in the story that were never resolved.',
      'Character Motivation Audits: Warns when a character acts inconsistently with their established psychological profile.',
      'Resolution Recommendations: Offers constructive narrative solutions to heal plot inconsistencies without rewriting entire chapters.'
    ],
    tips: 'Run the Plot Hole Detector whenever you complete a major act to catch discrepancies before beginning the next phase.'
  },
  {
    id: 'settings',
    chapterNumber: 'Chapter VIII',
    title: 'Archival Ambience & Export',
    subtitle: 'Customization, Soundscapes & Manuscript Printing',
    icon: Settings,
    quote: '"A craftsman is known by the reverence they hold for their instruments."',
    overview: 'Personalize your authorial sanctuary with atmospheric acoustic soundscapes, tactile cursor ripples, and export your completed manuscript for publication.',
    features: [
      'Ambient Victorian Audio: Gentle rain on windowpanes, crackling library fireplace, and vintage clock chimes.',
      'Parchment & Typewriter Customization: Adjust page contrast, font styling, and typewriter keypress acoustics.',
      'Archival Exporting: Export your completed book, dossiers, and timeline into print-ready PDF and formatted text.',
      'Encrypted Cloud Synchronization: Secure your manuscripts with Firebase Cloud Firestore authentication and private vault isolation.'
    ],
    tips: 'Export your manuscript regularly to keep an offline backup of your life\'s work.'
  }
];

interface ArchiveManualModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const ArchiveManualModal: React.FC<ArchiveManualModalProps> = ({ isOpen, onClose }) => {
  const [activePageIndex, setActivePageIndex] = useState(0);

  if (!isOpen) return null;

  const currentSection = manualSections[activePageIndex];
  const totalPages = manualSections.length;

  const handleNext = () => {
    if (activePageIndex < totalPages - 1) {
      sound.playPaperRustle();
      setActivePageIndex(prev => prev + 1);
    }
  };

  const handlePrev = () => {
    if (activePageIndex > 0) {
      sound.playPaperRustle();
      setActivePageIndex(prev => prev - 1);
    }
  };

  const handleSelectSection = (index: number) => {
    sound.playPaperRustle();
    setActivePageIndex(index);
  };

  const CurrentIcon = currentSection.icon;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-6 bg-black/85 backdrop-blur-md overflow-y-auto">
      {/* Antique Grimoire Book Container */}
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: 15 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className="relative w-full max-w-5xl bg-[#140F0B] rounded-2xl border-4 border-[#5E4427] shadow-[0_20px_70px_rgba(0,0,0,0.95),0_0_50px_rgba(196,154,97,0.3)] overflow-hidden flex flex-col my-auto"
        style={{
          backgroundImage: 'radial-gradient(circle at center, #1E1610 0%, #120C08 100%)'
        }}
      >
        {/* Ornate Gold Filigree Corners */}
        <div className="absolute top-2 left-2 text-[#C49A61]/40 text-lg select-none pointer-events-none">⚜</div>
        <div className="absolute top-2 right-2 text-[#C49A61]/40 text-lg select-none pointer-events-none">⚜</div>
        <div className="absolute bottom-2 left-2 text-[#C49A61]/40 text-lg select-none pointer-events-none">⚜</div>
        <div className="absolute bottom-2 right-2 text-[#C49A61]/40 text-lg select-none pointer-events-none">⚜</div>

        {/* Top Header Bar of the Leather Book */}
        <div className="relative px-6 py-4 border-b border-[#3B2B1D] bg-[#19110B]/90 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-[#C49A61]/20 border border-[#C49A61]/60 flex items-center justify-center text-[#F3D4A0]">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-serif text-lg sm:text-xl font-bold text-[#F4EDE2] tracking-wide flex items-center gap-2">
                Mythora Investigator's Manual
                <span className="text-[10px] font-sans font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-[#C49A61]/25 text-[#F3D4A0] border border-[#C49A61]/40">
                  Codex Guide
                </span>
              </h2>
              <p className="text-xs font-sans text-[#A69684]">
                Archival manual & guidebook for every studio chamber
              </p>
            </div>
          </div>

          {/* Close X Button */}
          <button
            onClick={() => {
              sound.playPaperRustle();
              onClose();
            }}
            className="w-8 h-8 rounded-full bg-[#261B13] hover:bg-[#3D2C20] border border-[#523B28] hover:border-[#C49A61] text-[#A69684] hover:text-[#F3D4A0] flex items-center justify-center transition-colors shadow"
            title="Close Manual"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Ribbon Bookmarks / Chapters Navigation Strip */}
        <div className="w-full bg-[#110C08] border-b border-[#2C1F15] px-4 py-2 flex items-center justify-between gap-2">
          {/* Scrollable Chapter Tabs */}
          <div className="flex items-center gap-1.5 overflow-x-auto scrollbar-none flex-1 min-w-0 pr-1">
            {manualSections.map((sec, idx) => {
              const Icon = sec.icon;
              const isSelected = idx === activePageIndex;
              return (
                <button
                  key={sec.id}
                  onClick={() => handleSelectSection(idx)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-sans font-medium whitespace-nowrap transition-all ${
                    isSelected
                      ? 'bg-[#C49A61] text-[#120D08] font-bold shadow-md shadow-[#C49A61]/20 scale-[1.02]'
                      : 'bg-[#1C140E] text-[#B09E8C] hover:bg-[#2A1E15] hover:text-[#EDE3D6] border border-[#3A2B1D]/50'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isSelected ? 'text-[#120D08]' : 'text-[#C49A61]'}`} />
                  <span>{sec.title}</span>
                </button>
              );
            })}
          </div>

          {/* Upper-Right Chapter Navigation Arrows */}
          <div className="flex items-center gap-1 shrink-0 pl-2 border-l border-[#2C1F15]">
            <button
              onClick={handlePrev}
              disabled={activePageIndex === 0}
              aria-label="Previous Chapter"
              title="Previous Chapter"
              className={`w-7 h-7 rounded-md border flex items-center justify-center transition-all ${
                activePageIndex === 0
                  ? 'opacity-30 cursor-not-allowed border-[#3A2B1D]/40 text-[#6B5A49]'
                  : 'bg-[#1C140E] hover:bg-[#2C1F15] border-[#4A3725] hover:border-[#C49A61] text-[#C49A61] hover:text-[#F3D4A0] shadow-sm hover:scale-105 active:scale-95'
              }`}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleNext}
              disabled={activePageIndex === totalPages - 1}
              aria-label="Next Chapter"
              title="Next Chapter"
              className={`w-7 h-7 rounded-md border flex items-center justify-center transition-all ${
                activePageIndex === totalPages - 1
                  ? 'opacity-30 cursor-not-allowed border-[#3A2B1D]/40 text-[#6B5A49]'
                  : 'bg-[#1C140E] hover:bg-[#2C1F15] border-[#4A3725] hover:border-[#C49A61] text-[#C49A61] hover:text-[#F3D4A0] shadow-sm hover:scale-105 active:scale-95'
              }`}
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Double-Page Spread Display */}
        <div className="p-4 sm:p-8 grid grid-cols-1 md:grid-cols-12 gap-6 min-h-[440px] max-h-[70vh] overflow-y-auto">
          {/* Left Page: Table of Contents & Chapter Illustration */}
          <div className="md:col-span-5 bg-[#EFE7D6] text-[#221A14] rounded-xl p-5 sm:p-6 shadow-inner border border-[#C8B898] flex flex-col justify-between relative overflow-hidden">
            {/* Subtle Aged Parchment Texture overlay */}
            <div 
              className="absolute inset-0 opacity-15 pointer-events-none mix-blend-multiply"
              style={{
                backgroundImage: 'radial-gradient(#805b38 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }}
            />

            <div className="relative z-10 space-y-4">
              <div className="flex items-center justify-between border-b border-[#8C6F48]/30 pb-2">
                <span className="font-typewriter text-[11px] font-bold text-[#8C6F48] uppercase tracking-widest">
                  {currentSection.chapterNumber}
                </span>
                <span className="font-sans text-[11px] font-semibold text-[#8C6F48]">
                  Folio {activePageIndex + 1} of {totalPages}
                </span>
              </div>

              <div className="flex items-center gap-3 pt-1">
                <div className="w-12 h-12 rounded-xl bg-[#2D2117] text-[#F3D4A0] border border-[#8C6F48] flex items-center justify-center shadow-md">
                  <CurrentIcon className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-serif text-xl sm:text-2xl font-bold text-[#1F1710] leading-tight">
                    {currentSection.title}
                  </h3>
                  <p className="font-sans text-xs text-[#5C4530] font-medium">
                    {currentSection.subtitle}
                  </p>
                </div>
              </div>

              {/* Decorative Gothic Quote */}
              <blockquote className="bg-[#DFD4BF]/70 border-l-4 border-[#8C6F48] p-3 rounded-r-lg font-serif italic text-xs text-[#3E2E20] leading-relaxed shadow-sm">
                {currentSection.quote}
              </blockquote>

              {/* Table of Contents Mini-List */}
              <div className="pt-2">
                <span className="font-typewriter text-[10px] font-bold text-[#7A603E] uppercase tracking-wider block mb-2">
                  All Chapters in this Tome:
                </span>
                <div className="space-y-1">
                  {manualSections.map((s, idx) => (
                    <button
                      key={s.id}
                      onClick={() => handleSelectSection(idx)}
                      className={`w-full text-left px-2 py-1 rounded text-[11px] font-sans flex items-center justify-between transition-colors ${
                        idx === activePageIndex
                          ? 'bg-[#8C6F48] text-white font-bold'
                          : 'text-[#4A3828] hover:bg-[#DFD4BF]'
                      }`}
                    >
                      <span className="truncate">{s.chapterNumber}: {s.title}</span>
                      <span className="text-[10px] opacity-75">p.{idx + 1}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Bottom Seal */}
            <div className="relative z-10 pt-4 flex items-center justify-between border-t border-[#8C6F48]/30 mt-3 text-[11px] font-sans text-[#7A603E]">
              <span>Mythora Codex Archival</span>
              <span>✦ Sanctum Approved</span>
            </div>
          </div>

          {/* Right Page: In-Depth Breakdown, Features & Pro-Tips */}
          <div className="md:col-span-7 bg-[#EFE7D6] text-[#221A14] rounded-xl p-5 sm:p-6 shadow-inner border border-[#C8B898] flex flex-col justify-between relative overflow-hidden">
            {/* Subtle Aged Parchment Texture overlay */}
            <div 
              className="absolute inset-0 opacity-15 pointer-events-none mix-blend-multiply"
              style={{
                backgroundImage: 'radial-gradient(#805b38 1px, transparent 1px)',
                backgroundSize: '16px 16px'
              }}
            />

            <div className="relative z-10 space-y-4">
              <div>
                <span className="font-typewriter text-[10px] font-bold text-[#8C6F48] uppercase tracking-widest block mb-1">
                  Chamber Overview
                </span>
                <p className="font-sans text-xs sm:text-sm text-[#2D2117] leading-relaxed font-normal">
                  {currentSection.overview}
                </p>
              </div>

              {/* Key Features List */}
              <div>
                <span className="font-typewriter text-[10px] font-bold text-[#8C6F48] uppercase tracking-widest block mb-2 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-[#8C6F48]" />
                  Chamber Capabilities & Functions
                </span>
                <ul className="space-y-2">
                  {currentSection.features.map((feat, fIdx) => (
                    <li key={fIdx} className="flex items-start gap-2 text-xs sm:text-[13px] text-[#33251B] leading-snug">
                      <CheckCircle2 className="w-4 h-4 text-[#8C6F48] shrink-0 mt-0.5" />
                      <span>{feat}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Author / Investigator Pro-Tip */}
              <div className="bg-[#DFD4BF]/90 border border-[#8C6F48]/40 rounded-lg p-3 space-y-1 shadow-sm">
                <span className="font-typewriter text-[10px] font-bold text-[#6D4C2B] uppercase tracking-widest flex items-center gap-1">
                  💡 Investigator's Pro-Tip
                </span>
                <p className="font-sans text-xs text-[#2A1E14] leading-relaxed">
                  {currentSection.tips}
                </p>
              </div>
            </div>

            {/* Bottom Page Navigation Controls */}
            <div className="relative z-10 pt-4 border-t border-[#8C6F48]/30 mt-4 flex items-center justify-between">
              <button
                onClick={handlePrev}
                disabled={activePageIndex === 0}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-sans font-bold transition-all ${
                  activePageIndex === 0
                    ? 'opacity-40 cursor-not-allowed text-[#7A603E]'
                    : 'bg-[#DFD4BF] hover:bg-[#D5C6AA] text-[#2D2117] shadow-sm'
                }`}
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                Previous Page
              </button>

              <span className="font-typewriter text-xs text-[#7A603E] font-semibold">
                Page {activePageIndex + 1} / {totalPages}
              </span>

              <button
                onClick={handleNext}
                disabled={activePageIndex === totalPages - 1}
                className={`flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-sans font-bold transition-all ${
                  activePageIndex === totalPages - 1
                    ? 'opacity-40 cursor-not-allowed text-[#7A603E]'
                    : 'bg-[#DFD4BF] hover:bg-[#D5C6AA] text-[#2D2117] shadow-sm'
                }`}
              >
                Next Page
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* Bottom Footer Action Bar */}
        <div className="px-6 py-4 bg-[#140E0A] border-t border-[#3B2B1D] flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-xs font-sans text-[#A69684] flex items-center gap-2">
            <span className="text-[#C49A61]">✦</span>
            <span>You can reopen this manual anytime via the <strong>Manual</strong> button in the top navigation bar.</span>
          </div>

          <button
            onClick={() => {
              sound.playPaperRustle();
              onClose();
            }}
            className="w-full sm:w-auto px-6 py-2.5 rounded-full bg-gradient-to-r from-[#C49A61] via-[#DDB47D] to-[#C49A61] hover:brightness-110 text-[#140E0A] font-sans text-xs uppercase tracking-wider font-bold shadow-[0_2px_15px_rgba(196,154,97,0.35)] transition-all hover:scale-105 active:scale-95 flex items-center justify-center gap-2"
          >
            <span>Close Manual & Enter Studio</span>
            <span>✦</span>
          </button>
        </div>
      </motion.div>
    </div>
  );
};
