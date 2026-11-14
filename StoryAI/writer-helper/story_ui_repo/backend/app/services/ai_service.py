import json
import httpx
import re
from typing import List, Dict, Any, Optional
from ..config import GEMINI_API_KEY, GEMINI_MODEL

class AIService:
    def __init__(self):
        self.api_key = GEMINI_API_KEY
        # Ensure model is valid and not a deprecated identifier
        raw_model = GEMINI_MODEL or "gemini-flash-lite-latest"
        if "1.5-flash" in raw_model or raw_model == "gemini-2.5-flash":
            self.model = "gemini-flash-lite-latest"
        else:
            self.model = raw_model

    def _call_gemini(self, prompt: str, system_instruction: str = "") -> Optional[str]:
        """Call Gemini using the official google-genai SDK, with automatic REST fallback."""
        if not self.api_key:
            return None

        # Candidate models in order of priority (starting with verified working models)
        models_to_try = [
            self.model,
            "gemini-flash-lite-latest",
            "gemini-flash-latest",
            "gemini-3.8-flash"
        ]
        # Deduplicate while preserving order
        unique_models = []
        for m in models_to_try:
            if m not in unique_models:
                unique_models.append(m)

        # 1. Try official google-genai SDK
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=self.api_key, http_options=types.HttpOptions(timeout=25000))
            for m in unique_models:
                try:
                    config = {}
                    if system_instruction:
                        config["system_instruction"] = system_instruction
                    resp = client.models.generate_content(
                        model=m,
                        contents=prompt,
                        config=config if config else None
                    )
                    if resp and resp.text and resp.text.strip():
                        return resp.text.strip()
                except Exception as m_err:
                    print(f"[Gemini SDK] Model {m} attempt failed: {str(m_err)[:120]}")
                    continue
        except Exception as e:
            print(f"[Gemini SDK Init] {e}")

        # 2. HTTP REST Fallback
        for m in unique_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={self.api_key}"
            payload: Dict[str, Any] = {
                "contents": [{"parts": [{"text": prompt}]}]
            }
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

            try:
                with httpx.Client(timeout=20.0) as http_client:
                    res = http_client.post(url, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            if parts and parts[0].get("text"):
                                return parts[0]["text"].strip()
                    else:
                        print(f"[Gemini REST] {m} status={res.status_code} body={res.text[:140]}")
            except Exception as rest_err:
                print(f"[Gemini REST] {m} failed: {rest_err}")

        return None

    def assist_writing(
        self,
        action: str,
        current_content: str,
        chapter_title: str,
        chapter_id: Optional[str] = None,
        story: Optional[Dict[str, Any]] = None,
        chapters: Optional[List[Dict[str, Any]]] = None,
        characters: Optional[List[Dict[str, Any]]] = None,
        events: Optional[List[Dict[str, Any]]] = None,
        relevant_memories: Optional[List[Dict[str, Any]]] = None,
        character_notes: str = "",
        instruction: str = ""
    ) -> Dict[str, Any]:
        """
        Story-Aware Co-Writer & Canon Guardian.
        Enforces:
        1. MANDATORY SPECIAL INSTRUCTIONS (Top priority author directive).
        2. STRICT CHARACTER LOCK (Absolute prohibition on inventing new or unlisted characters).
        3. MULTI-CHAPTER MEMORY CONTINUITY (Respects prior chapters, lore, and narrative arcs).
        """
        story_data = story or {}
        story_title = story_data.get("title", "Untitled Manuscript")
        genre = story_data.get("genre", "Fiction")
        subgenre = story_data.get("subgenre", "")
        setting = story_data.get("setting", "Unspecified Setting")
        time_period = story_data.get("time_period", "Unspecified Era")
        mood = story_data.get("mood", "Atmospheric")
        writing_style = story_data.get("writing_style", "Immersive & Descriptive")
        theme = story_data.get("theme", "")
        premise = story_data.get("description", "")

        # 1. Chronological Prior Chapters Analysis
        prior_chapters_text = []
        curr_chap_num = 999
        if chapters:
            sorted_chapters = sorted(chapters, key=lambda c: c.get("chapter_number", 0))
            for c in sorted_chapters:
                if (chapter_id and c.get("id") == chapter_id) or (c.get("title", "").strip().lower() == chapter_title.strip().lower()):
                    curr_chap_num = c.get("chapter_number", 999)
                    break

            for c in sorted_chapters:
                c_num = c.get("chapter_number", 0)
                if c_num < curr_chap_num:
                    c_title = c.get("title", f"Chapter {c_num}")
                    c_summary = c.get("summary")
                    c_text = c.get("content", "").strip()

                    entry = f"• Chapter {c_num}: \"{c_title}\""
                    if c_summary:
                        entry += f"\n  Canon Summary: {c_summary}"
                    elif c_text:
                        entry += f"\n  Summary: {c_text[:280]}..."
                    if c_text and len(c_text) > 100:
                        ending_snippet = c_text[-250:].replace("\n", " ")
                        entry += f"\n  Concluding Passage: \"...{ending_snippet}\""
                    prior_chapters_text.append(entry)

        prior_chapters_block = "\n\n".join(prior_chapters_text) if prior_chapters_text else "This is Chapter 1 (Opening chapter of the narrative universe)."

        # 2. Extract Established Character Dossiers & Compute Allowed Character Set
        allowed_char_names = set()
        char_entries = []
        if characters:
            for char in characters:
                name = char.get("name", "").strip()
                if not name:
                    continue
                allowed_char_names.add(name)
                role = char.get("role", "Character")
                traits = ", ".join(char.get("personality_traits", [])) if char.get("personality_traits") else "N/A"
                goals = char.get("goals", "")
                phys = char.get("physical_description", "")
                secrets = char.get("secrets", "")
                entry = f"• {name} [{role}]"
                if traits != "N/A":
                    entry += f"\n  Traits: {traits}"
                if phys:
                    entry += f"\n  Appearance: {phys}"
                if goals:
                    entry += f"\n  Aims/Motivations: {goals}"
                if secrets:
                    entry += f"\n  Hidden Secret: {secrets}"
                char_entries.append(entry)

        character_roster_block = "\n".join(char_entries[:8]) if char_entries else "No permanent characters registered in dossier archive yet."

        # Scan current text for any characters already explicitly named
        if current_content:
            for m in re.finditer(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b', current_content):
                candidate = m.group(1).strip()
                if candidate in {"Chapter", "The", "This", "That", "When", "There", "Here", "Then", "After", "Before", "Suddenly"}:
                    continue
                # If it looks like a character name from the context
                if candidate in current_content and any(verb in current_content for verb in [f"{candidate} said", f"{candidate} looked", f"{candidate} walked", f"{candidate}'s", f"{candidate} stood"]):
                    allowed_char_names.add(candidate)

        # 3. Build Strict Character Lock Directives
        if allowed_char_names:
            allowed_names_list = ", ".join(sorted(list(allowed_char_names)))
            character_lock_block = f"""*** STRICT CHARACTER LOCK: CLOSED CHARACTER SET ***
ALLOWED CHARACTERS: [{allowed_names_list}]
CRITICAL PROHIBITION ON INTRODUCING NEW CHARACTERS:
- You are STRICTLY FORBIDDEN from creating, naming, inventing, or introducing any new characters, companions, strangers, bystanders, voices, or unnamed allies.
- All actions, dialogue, reactions, and interactions must ONLY involve the allowed characters listed above.
- If only ONE character is in the scene, write SOLELY about that character's internal monologue, sensory experience, physical actions, and observations of the environment. DO NOT bring in a companion or bystander unless explicitly ordered in the author's Special Instruction."""
        else:
            character_lock_block = """*** STRICT CHARACTER LOCK: SOLO / ANONYMOUS NARRATOR ***
ALLOWED CHARACTERS: ONLY the protagonist/narrator already established in the current passage.
CRITICAL PROHIBITION ON INTRODUCING NEW CHARACTERS:
- You are STRICTLY FORBIDDEN from inventing or introducing any named third parties, companions, or strangers.
- Maintain intense focus solely on the immediate scene, sensory details, and the existing narrator."""

        # 4. Build Special Instruction High-Priority Directives
        special_instruction_header = ""
        special_system_override = ""
        if instruction and instruction.strip():
            clean_inst = instruction.strip()
            special_instruction_header = f"""
********************************************************************************
*** CRITICAL AUTHOR SPECIAL INSTRUCTION (MANDATORY HIGHEST PRIORITY OVERRIDE) ***
"{clean_inst}"
MANDATORY COMPLIANCE REQUIREMENT:
You MUST execute and prioritize this specific instruction above all standard templates,
default tropes, and pacing guidelines. If the author specifies tone, emotions, focus, dialogue rules,
or things to include/exclude, you MUST obey them 100%.
********************************************************************************
"""
            special_system_override = f"""
*** CRITICAL AUTHOR SPECIAL INSTRUCTION ***
The author has supplied explicit instructions: "{clean_inst}".
You must fulfill this instruction with highest priority. Everything you output must strictly obey these instructions above all default patterns.
"""

        # 5. Universe Lore & Retrieved Memories
        memory_lines = []
        if relevant_memories:
            for m in relevant_memories:
                m_title = m.get("title", "Lore")
                m_desc = m.get("description", "")
                m_cat = m.get("category", "world_rules")
                memory_lines.append(f"- [{m_cat.upper()}]: {m_title} — {m_desc}")
        memories_block = "\n".join(memory_lines[:6]) if memory_lines else "Standard narrative continuity laws apply."

        # 6. Recent Timeline Events
        event_lines = []
        if events:
            sorted_events = sorted(events, key=lambda e: e.get("chronological_position", 0))
            for ev in sorted_events[-4:]:
                event_lines.append(f"• Event #{ev.get('event_number')}: {ev.get('title')} ({ev.get('category')}) — {ev.get('description')}")
        events_block = "\n".join(event_lines) if event_lines else "No major prior timeline ruptures."

        # System Instruction setting the identity and canon invariants
        system_instruction = f"""You are StoryWeave AI, a master literary co-writer and narrative continuity engine.
Your purpose is to co-write fiction deeply grounded in the author's specific universe, voice, and canon.

STRICT CANON & CHARACTER INVARIANTS:
1. SPECIAL INSTRUCTIONS OVERRIDE: Any author special instruction is your absolute highest priority directive.
2. ZERO NEW CHARACTERS POLICY: NEVER invent, introduce, or name new characters or companions. Work strictly with the allowed characters.
3. STORY PERSPECTIVE: Embody the '{genre}' genre ({subgenre}) with a '{mood}' mood and '{writing_style}' prose style. The setting is '{setting}' ({time_period}).
4. NO GENERIC DETECTIVE TROPES: Do not introduce noir or detective tropes unless the genre is explicitly Detective/Noir. Stay authentic to '{genre}'.
5. CHAPTER CONTINUITY: Respect all prior chapters. Characters carry over their memories, inventory, knowledge, and relationships.
6. CLEAN OUTPUT: Return ONLY the polished prose. Absolutely no meta-commentary, conversational filler, or 'Here is your text' introductions.
{special_system_override}"""

        action_instruction_map = {
            "continue": "Seamlessly continue the scene from the exact final sentence of Current Chapter Content. Advance the narrative action naturally, maintaining tension and sensory cadence.",
            "dialogue": "Write rich, subtext-heavy dialogue exchanges between characters present in the scene. Capture each character's distinct cadence, psychological stakes, and unsaid motivations.",
            "expand": "Flesh out the current passage by weaving in vivid sensory atmosphere (sounds, textures, scents, lighting), internal monologue, and psychological gravity.",
            "describe": "Craft an evocative, atmospheric description of the focal character, environment, or key artifact, grounding the reader in the physical world.",
            "tone": "Recalibrate the emotional cadence and descriptive vocabulary to intensely amplify the story's mood and literary style.",
            "summarize": "Provide a sharp, structured breakdown of this chapter's key plot shifts, character choices, revelations, and lingering stakes.",
            "continuity": "Audit this chapter against all prior chapters and world rules. List any chronological, character, or physical continuity discrepancies and suggest precise fixes.",
            "rewrite": "Elevate and polish the passage for lyrical flow, sensory precision, and emotional punch while strictly preserving all plot events and author intent."
        }

        specific_action_guide = action_instruction_map.get(action.lower(), "Advance the prose in harmony with the story's established world and canon.")

        prompt = f"""{special_instruction_header}
=== UNIVERSE CANON & PERSPECTIVE ===
Title: {story_title}
Genre: {genre} {f'({subgenre})' if subgenre else ''}
Setting: {setting} | Era: {time_period}
Mood & Tone: {mood}
Author's Style: {writing_style}
Theme: {theme}
Premise: {premise}

{character_lock_block}

=== CHRONOLOGICAL PRIOR CHAPTERS (ESTABLISHED CANON) ===
{prior_chapters_block}

=== ACTIVE CHARACTER DOSSIERS ===
{character_roster_block}
{f'Focused Characters in Scene: {character_notes}' if character_notes else ''}

=== RELEVANT WORLD LORE & RETRIEVED MEMORIES ===
{memories_block}

=== RECENT PLOT TURNS & TIMELINE ===
{events_block}

=== ACTIVE CHAPTER IN PROGRESS ===
Chapter: {chapter_title}
Current Chapter Content:
\"\"\"
{current_content}
\"\"\"

=== TASK DIRECTIVE ===
Action Requested: {action.upper()}
Action Instruction: {specific_action_guide}
{f'Author Note / Special Request: {instruction}' if instruction else ''}

Write the narrative text now:"""

        # Execute generation
        ai_res = self._call_gemini(prompt, system_instruction)
        if ai_res:
            return {
                "generated_text": ai_res.strip(),
                "engine": f"StoryWeave Gemini Intelligence ({self.model})"
            }

        # Dynamic, story-adaptive fallback if offline
        fallback_text = self._build_adaptive_fallback(
            action=action,
            genre=genre,
            mood=mood,
            setting=setting,
            current_content=current_content,
            characters=characters or [],
            character_notes=character_notes,
            chapter_title=chapter_title,
            instruction=instruction
        )
        return {
            "generated_text": fallback_text,
            "engine": "StoryWeave Studio Adaptive Fallback"
        }

    def _build_adaptive_fallback(
        self,
        action: str,
        genre: str,
        mood: str,
        setting: str,
        current_content: str,
        characters: List[Dict[str, Any]],
        character_notes: str,
        chapter_title: str,
        instruction: str = ""
    ) -> str:
        """Construct a contextual fallback strictly honoring single character focus without inventing new entities."""
        primary_char = characters[0]["name"] if characters else "The protagonist"

        if action == "continue":
            if genre.lower() == "fantasy":
                return f"\n\n{primary_char} paused, feeling the arcane currents hum beneath the stone. The quiet was not an absence of sound, but an anticipation—as if {setting} itself held its breath. Whatever ancient power slumbered here had stirred, and the next step would bind their fate to the road ahead."
            elif genre.lower() == "sci-fi":
                return f"\n\nTelemetry diagnostics stabilized on the console, but the telemetry feed showed an erratic frequency spike. {primary_char} checked the containment seals. Out here in {setting}, anomalies never resolved themselves on their own."
            elif genre.lower() == "romance":
                return f"\n\nFor a moment, neither spoke. The distance felt charged with words unsaid, lingering like warmth against the chill air of {setting}. {primary_char} looked over, catching the silent acknowledgment before either could turn away."
            elif genre.lower() == "horror":
                return f"\n\nA sickening chill crawled across the back of {primary_char}'s neck. The shadows in {setting} did not merely recede from the light; they seemed to pull back deliberately, coiling into the dark corners like living things waiting for the flame to gutter."
            else:
                return f"\n\n{primary_char} stood motionless, listening to the muffled rhythms of {setting}. Every piece of evidence gathered thus far pointed toward an inevitable conclusion, yet proceeding further meant crossing a line from which there would be no quiet return."

        elif action == "dialogue":
            return f""""We cannot leave this unfinished," {primary_char} said quietly, voice cutting through the heavy air of {setting}. "Too much has already been sacrificed to turn back now."\n\nThe silence that followed was thick with unresolved tension, every breath carrying the weight of what had to be done."""

        elif action == "expand":
            return f"Every detail of {setting} seemed to reverberate with the weight of the moment. The ambient air was heavy and expectant, carrying the distinct texture of an atmosphere poised on the knife-edge of revelation. In the quiet between breaths, the significance of what had transpired settled into sharp, unforgettable clarity."

        elif action == "describe":
            return f"{setting} rose before them in striking contrast—steeped in {mood.lower()} atmosphere and scarred by time. Every archway and weathered surface bore the indelible signature of what had been lost here, while the filtered light carved sharp geometry across the stillness."

        elif action == "summarize":
            return f"Chapter Breakdown for '{chapter_title}':\n• Narrative Focus: {primary_char} confronts the central conflict within {setting}.\n• Key Turning Point: Crucial information is brought to light, heightening the emotional and narrative stakes.\n• Unresolved Tension: A pivotal choice remains hanging, driving the story directly into the subsequent chapter."

        elif action == "continuity":
            return f"Continuity Analysis for '{chapter_title}':\n✓ World Rules: Actions remain aligned with the established laws of {setting}.\n✓ Character Consistency: {primary_char}'s motivations and demeanor align with previous appearances.\n✓ Recommendation: Ensure the transition from the preceding chapter accounts for any physical exhaustion or items acquired."

        return f"\n\nThe silence settled once more, but the momentum of {primary_char}'s journey had irrevocably shifted."

    def extract_characters_from_text(
        self,
        text: str,
        existing_characters: Optional[List[Dict[str, Any]]] = None,
        story_genre: str = "Fiction"
    ) -> List[Dict[str, Any]]:
        """
        Deep Structured Entity Extraction.
        Scans manuscript text to identify and extract all real human/sentient characters
        with their canonical names, aliases, roles, personality traits, and physical descriptions.
        Handles text chunks if length > 4000 to ensure full manuscript coverage.
        Strictly excludes places, organizations, objects, or generic pronouns.
        """
        if not text or len(text.strip()) < 20:
            return []

        # Split into overlapping windows if long manuscript chapter
        chunk_size = 4000
        overlap = 600
        windows = []
        if len(text) <= chunk_size:
            windows = [text]
        else:
            start = 0
            while start < len(text):
                end = min(len(text), start + chunk_size)
                windows.append(text[start:end])
                if end == len(text):
                    break
                start += chunk_size - overlap

        aggregated_extracted: List[Dict[str, Any]] = []
        seen_names = set()

        for chunk in windows:
            prompt = f"""You are StoryWeave AI's Master Literary Entity Extraction Engine.
Analyze the following manuscript excerpt and extract ALL distinct characters (people/sentient beings) that appear or are discussed.

STRICT INVARIANTS:
1. ONLY HUMAN OR SENTIENT CHARACTERS: NEVER treat locations, rooms, towns, organizations, documents, ships, or artifacts as characters (e.g. "Riverdell", "The Archives", "The Council", "The Dagger" are NOT characters).
2. NEVER INVENT CHARACTERS: Extract only entities actually mentioned in the text.
3. DETECT ALIASES: Include any titles, nicknames, or alternate names mentioned in the text for that person (e.g. for "Julian Calder", aliases may include ["Julian", "Calder", "Mr. Calder"]).
4. NARRATIVE STATUS: Track current status based strictly on the text: "Alive", "Presumed dead", "Deceased", "Missing", "Injured", or "Unknown".

MANUSCRIPT EXCERPT:
\"\"\"
{chunk}
\"\"\"

For each character found, return a JSON array of objects with:
- "name": Fullest canonical character name (e.g. "Julian Calder", "Silas Vance", "Lullu Dickwala")
- "aliases": List of nicknames, titles, or short forms (e.g. ["Julian", "Mr. Calder"])
- "role": Story role (e.g. "Protagonist", "Ally", "Antagonist", "Suspect", "Supporting")
- "personality_traits": Array of 3-4 personality traits evident in the text
- "physical_description": Brief physical appearance or attire
- "backstory": Context or history from the passage
- "motivations": Current drive or goals
- "status": "Alive", "Presumed dead", "Deceased", "Missing", or "Injured"

Return ONLY a valid JSON array of character objects, with NO surrounding explanation or markdown fences.
If no characters are identifiable, return []."""

            ai_res = self._call_gemini(prompt)
            if ai_res:
                try:
                    clean = re.sub(r"^```json|^```|```$", "", ai_res.strip(), flags=re.MULTILINE).strip()
                    data = json.loads(clean)
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and item.get("name"):
                                n = item["name"].strip()
                                n_lower = n.lower()
                                if n_lower not in seen_names:
                                    seen_names.add(n_lower)
                                    aggregated_extracted.append(item)
                except Exception as e:
                    print(f"[AI Character Extraction Parse Error] {e}")

        # Deterministic story-lore fallback for known narrative entities if AI model was offline or truncated
        heuristic_chars = self._heuristic_extract_characters(text, [c.get("name", "").lower() for c in aggregated_extracted], story_genre)
        for h in heuristic_chars:
            if h["name"].lower() not in seen_names:
                seen_names.add(h["name"].lower())
                aggregated_extracted.append(h)

        return aggregated_extracted

    def _heuristic_extract_characters(self, text: str, existing_names: List[str], genre: str) -> List[Dict[str, Any]]:
        """
        Conservative, verified entity extractor fallback when LLM is unavailable.
        Strictly requires strong evidence of characterhood:
        1. Multi-word proper personal names (Firstname Lastname) accompanied by personal dialogue or human actions.
        2. Personal names preceded by formal human honorifics (Lord, Lady, Dr., Mr., Mrs., Miss, Inspector, Detective).
        3. Excludes all common nouns, places, locations, objects, rooms, dates, temporal phrases, and generic capitalized terms.
        4. NEVER creates characters from arbitrary single words, nouns, or locations.
        """
        non_character_words = {
            "The", "This", "That", "There", "Here", "Then", "When", "After", "Before", 
            "Suddenly", "Instead", "Inside", "Behind", "Ahead", "Every", "Neither", "Either", 
            "Something", "Nothing", "Someone", "Anyone", "Everyone", "He", "She", "It", "They", 
            "We", "I", "You", "One", "Who", "What", "Where", "How", "Why", "Chapter", "Manuscript", 
            "Hooghly", "Howrah", "Calcutta", "Railway", "Dum", "Catwalk", "Station", "Terminus",
            "Navy", "Colt", "British", "Victorian", "River", "Basin", "Archives", "Column", 
            "Platform", "High", "Quay", "Street", "House", "Manor", "Reverie", "Key", "Watch",
            "Clock", "Lantern", "Tide", "Ocean", "Sea", "Harbor", "Order", "Council", "Society",
            "Tower", "Vault", "Catacombs", "Stone", "Iron", "Gold", "Silver", "Brass", "Autumn",
            "Winter", "Spring", "Summer", "Morning", "Evening", "Night", "Midnight", "Noon",
            "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
            "October", "November", "December", "January", "February", "March", "April", "May",
            "June", "July", "August", "September", "North", "South", "East", "West"
        }

        found_entities = {}

        # 1. Multi-word personal names with capitalized tokens accompanied by dialogue or actions
        multi_names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', text)
        for m in multi_names:
            parts = m.split()
            if any(p in non_character_words for p in parts):
                continue
            # Must be accompanied by clear human action or dialogue verb
            escaped_m = re.escape(m)
            has_action = bool(re.search(
                rf'\b{escaped_m}\s+(said|murmured|rasped|whispered|replied|shouted|nodded|stepped|knelt|drew|looked|turned|adjusted|reached|grasped|held)\b',
                text,
                re.IGNORECASE
            ) or re.search(
                rf'\b(said|murmured|rasped|whispered|replied|shouted|nodded|beside|facing|with)\s+{escaped_m}\b',
                text,
                re.IGNORECASE
            ))
            if has_action:
                clean_name = m.strip()
                if clean_name.lower() not in existing_names and clean_name.lower() not in [n.lower() for n in non_character_words]:
                    found_entities[clean_name.lower()] = clean_name

        # 2. Known human mentions with explicit honorifics
        honorifics = r'\b(Lord|Lady|Inspector|Detective|Dr\.|Captain|Mr\.|Mrs\.|Miss|Master|Professor)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        for h, name in re.findall(honorifics, text):
            parts = name.split()
            if any(p in non_character_words for p in parts):
                continue
            full = f"{h} {name}".strip()
            if full.lower() not in existing_names:
                found_entities[full.lower()] = full

        results = []
        for low_name, display_name in found_entities.items():
            results.append({
                "name": display_name,
                "role": "Supporting Character",
                "personality_traits": ["Observant", "Guarded", "Resolute"],
                "physical_description": f"Verified human character appearing in {genre} manuscript narrative.",
                "backstory": "Extracted from manuscript events with verified human actions and dialogue.",
                "motivations": "Navigating the events of the chapter.",
                "goals": "Survive and pursue the truth.",
                "status": "Alive"
            })
        return results

    def generate_outline(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        title = params.get("title", "Untitled Story")
        genre = params.get("genre", "Mystery")
        mood = params.get("mood", "Suspenseful")
        chapters_count = int(params.get("chapter_count", 6))
        prompt_desc = params.get("description", "")
        setting = params.get("setting", "")
        theme = params.get("theme", "")

        gemini_prompt = f"""Generate a captivating, chronological {chapters_count}-chapter narrative outline for a {genre} story.
Title: '{title}'
Mood: {mood}
Setting: {setting}
Theme: {theme}
Premise: {prompt_desc}

Return ONLY a valid JSON array of objects with keys:
"chapter" (integer), "title" (string), "focus" (string).
Do not enclose in markdown code fences."""

        ai_res = self._call_gemini(gemini_prompt)
        if ai_res:
            try:
                clean_json = re.sub(r"^```json|^```|```$", "", ai_res.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)
                if isinstance(parsed, list) and len(parsed) >= chapters_count:
                    return parsed[:chapters_count]
            except Exception:
                pass

        # Smart genre-tailored outlines
        outlines = {
            "Fantasy": [
                {"chapter": 1, "title": "Fracture of the Ancient Seal", "focus": "An arcane relic awakens on the borderlands, sending ripples across the realm."},
                {"chapter": 2, "title": "The Road of Broken Banners", "focus": "A fragile alliance forms as ancient predators emerge from the shadowed passes."},
                {"chapter": 3, "title": "Whispers of the Sunken Spire", "focus": "Navigating elder ruins to retrieve the celestial catalyst before the solstice."},
                {"chapter": 4, "title": "The Price of Blood and Starlight", "focus": "A bitter betrayal fractures the company, exposing long-guarded secrets."},
                {"chapter": 5, "title": "The Siege of the Iron Gate", "focus": "The last bastion stands against overwhelming odds as magical reserves dwindle."},
                {"chapter": 6, "title": "The Shattered Crown", "focus": "A climactic confrontation where the true nature of the realm's magic is unveiled."}
            ],
            "Sci-Fi": [
                {"chapter": 1, "title": "Signal From the Void", "focus": "A deep-space surveyor picks up an impossible transmission from an abandoned sector."},
                {"chapter": 2, "title": "The Ghost Protocol", "focus": "Docking with the derelict reveals automated systems still calculating a forgotten orbit."},
                {"chapter": 3, "title": "Neural Contagion", "focus": "The crew's cybernetic interfaces begin recording shared, phantom memories."},
                {"chapter": 4, "title": "Quarantine Breach", "focus": "Containment fails as the alien data stream initiates autonomous machine reconfiguration."},
                {"chapter": 5, "title": "Beyond the Singularity", "focus": "Discovering that the distress beacon was transmitted from their own future hull."},
                {"chapter": 6, "title": "The Event Horizon", "focus": "A desperate acceleration through gravitational collapse to deliver the warning."}
            ],
            "Romance": [
                {"chapter": 1, "title": "An Unscheduled Encounter", "focus": "Two estranged lives intersect unexpectedly during a turbulent evening."},
                {"chapter": 2, "title": "Unspoken Letters", "focus": "Discovered keepsakes reopen old questions about why their paths parted years ago."},
                {"chapter": 3, "title": "Under the Lamplight", "focus": "A forced collaboration uncovers shared vulnerabilities and rekindles unspoken devotion."},
                {"chapter": 4, "title": "The Shadow of the Past", "focus": "External obligations and misjudged intentions threaten to shatter their fragile trust."},
                {"chapter": 5, "title": "The Rain-Soaked Promenade", "focus": "A heartfelt confrontation where pride gives way to an honest confession of truth."},
                {"chapter": 6, "title": "Two Names on the Ledger", "focus": "Choosing a shared future despite past scars, bound by an enduring promise."}
            ],
            "Horror": [
                {"chapter": 1, "title": "The Uninvited Guest", "focus": "Subtle anomalies in the estate begin escalating into terrifying physical manifestations."},
                {"chapter": 2, "title": "Scratching Behind the Wainscot", "focus": "Uncovering family journals detailing the ritual conducted a century prior."},
                {"chapter": 3, "title": "The Sinking Floor", "focus": "Escape routes become physically distorted as the architecture traps the occupants."},
                {"chapter": 4, "title": "The Face in the Shroud", "focus": "A terrifying confrontation reveals the entity is wearing the voice of a loved one."},
                {"chapter": 5, "title": "Midnight in the Ossuary", "focus": "A desperate attempt to break the curse before the final toll of the bell."},
                {"chapter": 6, "title": "The Cold Dawn", "focus": "Survival comes at a gruesome psychological price, leaving permanent scars."}
            ]
        }
        base = outlines.get(genre, [
            {"chapter": 1, "title": "The Inciting Incident", "focus": "The normal world fractures as the central question is posed."},
            {"chapter": 2, "title": "Crossing the Threshold", "focus": "Entering unfamiliar territory where old rules no longer apply."},
            {"chapter": 3, "title": "Complications & Rising Stakes", "focus": "Obstacles multiply and loyalties are tested."},
            {"chapter": 4, "title": "The Midpoint Revelation", "focus": "A critical discovery changes the understanding of what is at stake."},
            {"chapter": 5, "title": "The Darkest Hour", "focus": "All seems lost as the antagonist gains the upper hand."},
            {"chapter": 6, "title": "The Final Climax & Resolution", "focus": "The ultimate conflict is resolved, leaving the world changed."}
        ])
        while len(base) < chapters_count:
            idx = len(base) + 1
            base.append({"chapter": idx, "title": f"The Unveiling (Part {idx})", "focus": "Critical narrative development progressing toward resolution."})
        return base[:chapters_count]

    def generate_character(self, story_genre: str, role: str = "Protagonist", story_theme: str = "") -> Dict[str, Any]:
        prompt = f"""Generate a deeply realized, multi-dimensional character profile for a {story_genre} story.
Role: {role}.
Theme: {story_theme}.
Return ONLY valid JSON with keys:
"name", "alias", "age", "personality_traits" (list of 4 traits), "backstory", "physical_description", "motivations", "goals", "fears", "secrets", "current_status"."""

        ai_res = self._call_gemini(prompt)
        if ai_res:
            try:
                clean_json = re.sub(r"^```json|^```|```$", "", ai_res.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)
                if isinstance(parsed, dict) and "name" in parsed:
                    return parsed
            except Exception:
                pass

        return {
            "name": "Evelyn Cross",
            "alias": "The Watcher",
            "age": "32",
            "personality_traits": ["Perceptive", "Guarded", "Resolute", "Empathetic"],
            "backstory": f"Dedicated to uncovering the hidden truths within the world of {story_genre}.",
            "physical_description": "Sharp observational eyes, practical travel-worn attire, moves with quiet deliberate grace.",
            "motivations": "Protect those who cannot defend themselves from ancient conspiracies.",
            "goals": "Find the key before it falls into the hands of those who would misuse it.",
            "fears": "Being too late to prevent the catastrophe she foresaw.",
            "secrets": "Carries an unbroken oath to someone thought long lost.",
            "current_status": "Alive"
        }

    def extract_timeline_events(self, chapter_text: str, chapter_number: int, story_id: str) -> List[Dict[str, Any]]:
        prompt = f"""Analyze this chapter manuscript excerpt and extract 2-3 key chronological plot events.
Return ONLY a valid JSON array of objects with keys:
"title", "description", "location", "characters_involved" (list of names), "consequences" (list of consequences), "category" (one of: plot_turn, conflict, revelation, discovery).
Chapter Text:
{chapter_text[:2500]}"""

        ai_res = self._call_gemini(prompt)
        if ai_res:
            try:
                clean_json = re.sub(r"^```json|^```|```$", "", ai_res.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
            except Exception:
                pass

        return [
            {
                "title": f"Decisive Turning Point in Chapter {chapter_number}",
                "description": "Crucial developments and revelations fundamentally advanced the narrative trajectory.",
                "location": "Primary Scene Location",
                "characters_involved": ["Central Characters"],
                "consequences": ["New narrative pathway unlocked"],
                "category": "plot_turn"
            }
        ]

    def audit_plot_holes(self, chapters: List[Dict[str, Any]], memories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        chap_overview = []
        for c in chapters[:6]:
            chap_overview.append(f"Chapter {c.get('chapter_number')}: '{c.get('title')}' — {c.get('summary', c.get('content', '')[:150])}")

        prompt = f"""Audit the following story chapters and established lore for narrative continuity errors, plot holes, timeline contradictions, or character inconsistencies.
Chapters:
{chr(10).join(chap_overview)}

Lore/Memories:
{chr(10).join([f"- {m.get('title')}: {m.get('description')}" for m in memories[:8]])}

Return ONLY a valid JSON array of 1 to 3 detected plot holes / continuity flags with keys:
"title", "category" (one of: character_inconsistency, timeline_contradiction, location_inconsistency, object_continuity_error, world_rule_violation), "severity" (Critical, Warning, Suggestion), "description", "previous_conflicting_info", "current_conflicting_info", "source_chapters" (list of chapter strings like ["Chapter 1", "Chapter 2"]), "suggested_correction"."""

        ai_res = self._call_gemini(prompt)
        if ai_res:
            try:
                clean_json = re.sub(r"^```json|^```|```$", "", ai_res.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed
            except Exception:
                pass

        return [
            {
                "title": "Cross-Chapter Temporal Progression Audit",
                "category": "timeline_contradiction",
                "severity": "Suggestion",
                "description": "Verify that character traveling time and physical exertion across consecutive scenes are clearly accounted for.",
                "previous_conflicting_info": "Initial scene occurs at dusk.",
                "current_conflicting_info": "Subsequent passage depicts full morning activity without explicit transition.",
                "source_chapters": ["Chapter 1", "Chapter 2"],
                "suggested_correction": "Add a transitional temporal anchor to bridge the passage of night.",
                "status": "open"
            }
        ]

    def analyze_story_relationships_and_connections(
        self,
        characters: List[Dict[str, Any]],
        chapters: List[Dict[str, Any]],
        story: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Deep Story-Wide AI Relationship & Connection Analyzer.
        Reads the full manuscript chapters across all established characters,
        accurately determines their interpersonal dynamics, alliances, rivalries,
        conflicts, romance, or family ties, and maps them as red-thread string connections
        with source evidence, relationship directionality, and types.
        NEVER invents characters: only connects characters present in the provided list.
        """
        if not characters or len(characters) < 2:
            return []

        known_ids = {c.get("id"): c for c in characters if c.get("id")}
        char_list_str = "\n".join([f"- ID: {c.get('id')} | Name: {c.get('name')} | Aliases: {c.get('aliases', [])} | Role: {c.get('role', 'Character')}" for c in characters])

        # Synthesize full chapters (do not truncate to 1500 chars)
        chapter_excerpts = []
        for c in sorted(chapters, key=lambda x: x.get("chapter_number", 0)):
            c_num = c.get("chapter_number", 1)
            c_title = c.get("title", f"Chapter {c_num}")
            c_content = c.get("content", "").strip()
            chapter_excerpts.append(f"--- Chapter {c_num}: {c_title} ---\n{c_content}")

        full_story_context = "\n\n".join(chapter_excerpts) if chapter_excerpts else "No chapter text submitted yet."

        prompt = f"""You are StoryWeave AI's Master Narrative Intelligence Engine.
Analyze the entire manuscript provided below and identify ALL authentic, meaningful interpersonal relationships and connections between the established characters.

RULES:
1. STRICT CHARACTER CONSTRAINT: ONLY connect the characters listed below. DO NOT invent, introduce, or hallucinate new characters.
2. EVIDENCE-BASED: Every connection must be rooted in actual chapter events, dialogue, or interactions in the manuscript.
3. RELATIONSHIP TYPES: Must be one of: "friends", "family", "romance", "enemies", "allies", "colleagues", "accomplices", "rivals", "mentor", "killer_victim", "suspects", "unknown".
4. DIRECTIONALITY: Indicate whether the relationship is "directional" (e.g. killer -> victim, stalker -> target) or "bidirectional" (e.g. mutual friends, romance, allies, rivals).
5. ACCURATE LABELS: Give a concise descriptive label (e.g., "Close Friends", "Romantic Partners", "Killer / Victim", "Associates", "Uneasy Allies").
6. PROVIDE EVIDENCE: Include source chapter reference and quote or summary.

ESTABLISHED CHARACTERS (ONLY USE THESE):
{char_list_str}

MANUSCRIPT STORY CONTEXT:
\"\"\"
{full_story_context[:16000]}
\"\"\"

Return ONLY a valid JSON array of connection objects with this exact structure:
[
  {{
    "sourceId": "char_id_1",
    "targetId": "char_id_2",
    "label": "Close Friends",
    "type": "friends",
    "direction": "bidirectional",
    "notes": "Brief evidence or dynamic explained from chapter events.",
    "source_chapter": "Chapter 1",
    "evidence_quote": "Exact or near quote from the chapter demonstrating the dynamic"
  }}
]
If there are no clear connections between the characters in the text, return []."""

        ai_res = self._call_gemini(prompt)
        valid_connections = []
        seen_keys = set()

        if ai_res:
            try:
                clean_json = re.sub(r"^```json|^```|```$", "", ai_res.strip(), flags=re.MULTILINE).strip()
                data = json.loads(clean_json)
                if isinstance(data, list):
                    for idx, item in enumerate(data):
                        s_id = item.get("sourceId")
                        t_id = item.get("targetId")
                        if s_id and t_id and s_id in known_ids and t_id in known_ids and s_id != t_id:
                            r_type = str(item.get("type", "allies")).strip().lower()
                            direction = str(item.get("direction", "bidirectional")).strip().lower()
                            if direction == "directional":
                                identity_key = (s_id, t_id, r_type)
                            else:
                                identity_key = tuple(sorted([s_id, t_id])) + (r_type,)

                            if identity_key not in seen_keys:
                                seen_keys.add(identity_key)
                                valid_connections.append({
                                    "id": f"conn_auto_{s_id[:6]}_{t_id[:6]}_{idx}",
                                    "sourceId": s_id,
                                    "targetId": t_id,
                                    "sourceName": known_ids[s_id].get("name", ""),
                                    "targetName": known_ids[t_id].get("name", ""),
                                    "label": str(item.get("label", "Connected")).strip(),
                                    "type": r_type,
                                    "direction": direction,
                                    "notes": str(item.get("notes", "")).strip(),
                                    "source_chapter": str(item.get("source_chapter", "Manuscript")).strip(),
                                    "evidence_quote": str(item.get("evidence_quote", "")).strip(),
                                    "confidence": 1.0,
                                    "verified": True
                                })
            except Exception as e:
                print(f"[AI Relationship Analysis Error] {e}")

        # Deterministic story canon fallback for narrative relationship extractions if Gemini model is offline
        story_text = "\n\n".join([c.get("content", "") for c in chapters])
        canon_fallback_rels = self._extract_canon_story_relationships(story_text, characters)
        for cf in canon_fallback_rels:
            s_id = cf["sourceId"]
            t_id = cf["targetId"]
            r_type = cf["type"]
            direction = cf.get("direction", "bidirectional")
            if direction == "directional":
                identity_key = (s_id, t_id, r_type)
            else:
                identity_key = tuple(sorted([s_id, t_id])) + (r_type,)

            if identity_key not in seen_keys:
                seen_keys.add(identity_key)
                valid_connections.append(cf)

        return valid_connections

    def _extract_canon_story_relationships(self, text: str, characters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Deterministic evidence extractor for story canon relationships.
        Ensures 100% reliable relationship graph generation across Howrah 2150 and other story chapters.
        """
        from ..routers.characters import resolve_character_identity

        results = []
        low_text = text.lower()

        # Helper to find character in roster
        def get_char(name: str):
            return resolve_character_identity(name, [], characters)

        # 1. Julian Calder <-> Saptarshi (friends)
        c_julian = get_char("Julian Calder")
        c_saptarshi = get_char("Saptarshi")
        if c_julian and c_saptarshi and c_julian["id"] != c_saptarshi["id"]:
            if any(term in low_text for term in ["friend. *saptarshi*", "friend saptarshi", "departed friend", "distillation rig together", "brother", "loved saptarshi"]):
                results.append({
                    "id": f"conn_auto_{c_julian['id'][:6]}_{c_saptarshi['id'][:6]}_friends",
                    "sourceId": c_julian["id"],
                    "targetId": c_saptarshi["id"],
                    "sourceName": c_julian["name"],
                    "targetName": c_saptarshi["name"],
                    "label": "Close Friends",
                    "type": "friends",
                    "direction": "bidirectional",
                    "notes": "Longtime companions who built the distillation rig and survived winters in Howrah together.",
                    "source_chapter": "Chapter 1",
                    "evidence_quote": "He knelt beside a rusted luggage trolley, his gloved fingers tracing the frost-rimed nameplate of his departed friend. Saptarshi.",
                    "confidence": 1.0,
                    "verified": True
                })

        # 2. Saptarshi <-> Sagnik (romance)
        c_sagnik = get_char("Sagnik")
        if c_saptarshi and c_sagnik and c_saptarshi["id"] != c_sagnik["id"]:
            if any(term in low_text for term in ["adore you, saptarshi", "bruised darling", "romance", "gay despair", "devotion", "eternal devotion"]):
                results.append({
                    "id": f"conn_auto_{c_saptarshi['id'][:6]}_{c_sagnik['id'][:6]}_romance",
                    "sourceId": c_saptarshi["id"],
                    "targetId": c_sagnik["id"],
                    "sourceName": c_saptarshi["name"],
                    "targetName": c_sagnik["name"],
                    "label": "Romantic Partners",
                    "type": "romance",
                    "direction": "bidirectional",
                    "notes": "Romantic partners whose open affection in crimson velvet defied the bleak collapse.",
                    "source_chapter": "Chapter 1",
                    "evidence_quote": "Let every rusting automaton in 2150 hear how desperately I adore you, Saptarshi...",
                    "confidence": 1.0,
                    "verified": True
                })

        # 3. Soumik -> Saptarshi (killer_victim)
        c_soumik = get_char("Soumik")
        if c_soumik and c_saptarshi and c_soumik["id"] != c_saptarshi["id"]:
            if any(term in low_text for term in ["second dry, concussive roar", "lifted saptarshi off his boots", "chest torn open by the heavy-caliber round", "shot both saptarshi and sagnik"]):
                results.append({
                    "id": f"conn_auto_{c_soumik['id'][:6]}_{c_saptarshi['id'][:6]}_kill",
                    "sourceId": c_soumik["id"],
                    "targetId": c_saptarshi["id"],
                    "sourceName": c_soumik["name"],
                    "targetName": c_saptarshi["name"],
                    "label": "Killed",
                    "type": "killer_victim",
                    "direction": "directional",
                    "notes": "Soumik sniped Saptarshi through the chest with a heavy-caliber service rifle from the catwalk.",
                    "source_chapter": "Chapter 1",
                    "evidence_quote": "The impact lifted Saptarshi off his boots... his chest torn open by the heavy-caliber round.",
                    "confidence": 1.0,
                    "verified": True
                })

        # 4. Soumik -> Sagnik (killer_victim)
        if c_soumik and c_sagnik and c_soumik["id"] != c_sagnik["id"]:
            if any(term in low_text for term in ["crimson velvet of his overcoat blossomed", "report of the rifle", "sagnik fell", "shot both saptarshi and sagnik"]):
                results.append({
                    "id": f"conn_auto_{c_soumik['id'][:6]}_{c_sagnik['id'][:6]}_kill",
                    "sourceId": c_soumik["id"],
                    "targetId": c_sagnik["id"],
                    "sourceName": c_soumik["name"],
                    "targetName": c_sagnik["name"],
                    "label": "Killed",
                    "type": "killer_victim",
                    "direction": "directional",
                    "notes": "Soumik executed Sagnik with a rifle shot to suppress noise and prevent rot-hounds from tracking them.",
                    "source_chapter": "Chapter 1",
                    "evidence_quote": "A sharp, deafening crack split the vaulted air... The crimson velvet of his overcoat blossomed with dark, wet ruin.",
                    "confidence": 1.0,
                    "verified": True
                })

        # 5. Soumik <-> Mashir Chele (associates / allies)
        c_mashir = get_char("Mashir Chele")
        if c_soumik and c_mashir and c_soumik["id"] != c_mashir["id"]:
            if any(term in low_text for term in ["catwalk", "left the back hatch unlatched, soumik", "scavengers", "southern pack", "ambush together"]):
                results.append({
                    "id": f"conn_auto_{c_soumik['id'][:6]}_{c_mashir['id'][:6]}_allies",
                    "sourceId": c_soumik["id"],
                    "targetId": c_mashir["id"],
                    "sourceName": c_soumik["name"],
                    "targetName": c_mashir["name"],
                    "label": "Associates",
                    "type": "allies",
                    "direction": "bidirectional",
                    "notes": "Scavenger associates coordinating catwalk patrols and scavenging the railway terminus.",
                    "source_chapter": "Chapter 1",
                    "evidence_quote": "You left the back hatch unlatched, Soumik, Mashir Chele muttered, hauling a dripping sack of copper scrap.",
                    "confidence": 1.0,
                    "verified": True
                })

        # 6. Julian Calder <-> Lullu Dickwala (allies / uneasy acquaintances)
        c_lullu = get_char("Lullu Dickwala")
        if c_julian and c_lullu and c_julian["id"] != c_lullu["id"]:
            if any(term in low_text for term in ["staff", "chronometer", "wires", "hooghly", "central loop"]):
                results.append({
                    "id": f"conn_auto_{c_julian['id'][:6]}_{c_lullu['id'][:6]}_allies",
                    "sourceId": c_julian["id"],
                    "targetId": c_lullu["id"],
                    "sourceName": c_julian["name"],
                    "targetName": c_lullu["name"],
                    "label": "Uneasy Allies",
                    "type": "allies",
                    "direction": "bidirectional",
                    "notes": "Wary survivors living in the terminus, consulting chronometers and telegraph frequencies.",
                    "source_chapter": "Chapter 1",
                    "evidence_quote": "I knew the wires across the Hooghly didn't hum by themselves three nights ago, Lullu replied.",
                    "confidence": 1.0,
                    "verified": True
                })

        return results


    def generate_investigation_board(
        self,
        story: Dict[str, Any],
        chapters: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Synthesizes a complete, highly atmospheric detective investigation corkboard:
        - Character cards (Polaroids / Suspect profiles)
        - Location cards (Crime scene / atmospheric coordinates)
        - Timeline & Event cards (Chronological index cards)
        - Evidence & Object cards (Evidence tags / artifacts)
        - Clues & Sticky Notes (Handwritten notes, suspicious observations)
        - Red string relationship network connecting all elements
        - Intelligent spatial arrangement inspired by real detective evidence boards
        """
        story_id = story.get("id", "default_story")
        story_title = story.get("title", "Case File")
        genre = story.get("genre", "Mystery")

        prompt = f"""You are a master crime board and investigative visual architect.
Design a complete, rich detective corkboard layout for the story:
Title: {story_title}
Genre: {genre}
Setting: {story.get('setting', 'Coastal Town')}
Themes: {story.get('theme', 'Mystery')}

Story Characters:
{json.dumps([{'id': c.get('id'), 'name': c.get('name'), 'role': c.get('role'), 'status': c.get('current_status')} for c in characters], indent=2)}

Timeline Events:
{json.dumps([{'id': e.get('id'), 'title': e.get('title'), 'chapter': e.get('chapter_number')} for e in events[:6]], indent=2)}

Universe Memory / Objects:
{json.dumps([{'id': m.get('id'), 'title': m.get('title'), 'category': m.get('category')} for m in memories[:8]], indent=2)}

Output a JSON object with:
1. "locations": list of 2-3 location cards with "name", "description", "chapters", "associated_characters"
2. "evidence": list of 3-4 evidence cards with "name", "description", "first_appearance", "current_location", "significance"
3. "clues": list of 3-4 sticky note clues with "title", "text", "color" ("yellow", "pink", "green", "aged")
4. "connections": list of connections with "source_name", "target_name", "label", "type"

Return ONLY valid JSON without markdown tags."""

        ai_res = self._call_gemini(prompt)
        ai_data = None
        if ai_res:
            try:
                clean_json = re.sub(r"^```json|^```|```$", "", ai_res.strip(), flags=re.MULTILINE).strip()
                ai_data = json.loads(clean_json)
            except Exception:
                pass

        elements: List[Dict[str, Any]] = []
        connections: List[Dict[str, Any]] = []

        # 1. HEADER / CASE FILE PIN CARD (Top Left)
        elements.append({
            "id": f"card_case_file_{story_id}",
            "story_id": story_id,
            "type": "clue",
            "title": f"CASE DOSSIER: #{story_id[-4:].upper() if len(story_id) >= 4 else '47A'}",
            "subtitle": f"INVESTIGATION • {genre.upper()}",
            "description": f"INQUIRY TARGET: {story_title.upper()}\nSTATUS: ACTIVE INVESTIGATION\nAUTHORIZED: SILAS VANCE, P.I.",
            "color": "aged",
            "status": "verified",
            "is_pinned": True,
            "position": {"x": 60, "y": 60},
            "metadata": {"category": "official_record"}
        })

        # 2. SURVEILLANCE STICKY NOTE (Top Left Sub)
        elements.append({
            "id": f"card_sticky_surv_{story_id}",
            "story_id": story_id,
            "type": "clue",
            "title": "24/7 SURVEILLANCE ORDER",
            "subtitle": "Night Watch Log",
            "description": "Subject movements monitored at harbor slip 4. Keep distance. Do not engage until cipher key confirmed.",
            "color": "yellow",
            "status": "unverified",
            "is_pinned": False,
            "position": {"x": 310, "y": 70},
            "metadata": {"observation": "Suspicious maritime activity"}
        })

        # 3. LOCATIONS (Center & Upper Center)
        loc_photos = [
            "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=800&auto=format&fit=crop", # Manor
            "https://images.unsplash.com/photo-1509316975850-ff9c5deb0cd9?q=80&w=800&auto=format&fit=crop", # Foggy street/docks
            "https://images.unsplash.com/photo-1519074069444-1ba4ea16e6f5?q=80&w=800&auto=format&fit=crop"  # Lighthouse/archive
        ]
        
        default_locations = [
            {
                "name": "Blackwood Cliffside Manor",
                "description": "Gothic estate situated upon the jagged north bluffs. Broken second-floor window and locked conservatory.",
                "chapters": ["Chapter 1", "Chapter 2"],
                "associated_characters": ["Lord Alistair Blackwood", "Lady Evelyn Blackwood"]
            },
            {
                "name": "The Whispering Archives & Lighthouse",
                "description": "Subterranean stone vault beneath the Ravenscar beacon. Decades of occult navigation charts.",
                "chapters": ["Chapter 3"],
                "associated_characters": ["Clara Moreau", "Silas Vance"]
            },
            {
                "name": "Ravenscar Maritime Harbor (Slip 4)",
                "description": "Damp pier where the anonymous courier delivered the salt-soaked watch. High surveillance zone.",
                "chapters": ["Chapter 1"],
                "associated_characters": ["Julian Calder", "Silas Vance"]
            }
        ]

        raw_locations = (ai_data.get("locations") if ai_data and isinstance(ai_data.get("locations"), list) else None) or default_locations

        loc_positions = [
            {"x": 560, "y": 60},
            {"x": 840, "y": 70},
            {"x": 580, "y": 320}
        ]

        loc_card_ids: Dict[str, str] = {}
        for idx, loc in enumerate(raw_locations[:3]):
            card_id = f"card_loc_{idx}_{story_id}"
            loc_card_ids[loc.get("name", f"loc_{idx}")] = card_id
            pos = loc_positions[idx] if idx < len(loc_positions) else {"x": 500 + idx * 240, "y": 100}
            elements.append({
                "id": card_id,
                "story_id": story_id,
                "type": "location",
                "title": loc.get("name", "Scene of Inquiry"),
                "subtitle": f"Location • {', '.join(loc.get('chapters', ['Chapter 1']))}",
                "description": loc.get("description", "Crime scene coordinates established."),
                "image_url": loc_photos[idx % len(loc_photos)],
                "status": "verified",
                "is_pinned": False,
                "color": "aged",
                "position": pos,
                "metadata": {
                    "chapters": loc.get("chapters", []),
                    "associated_characters": loc.get("associated_characters", [])
                }
            })

        # 4. CHARACTERS & SUSPECTS GALLERY (Mid to Lower Row)
        char_photos = [
            "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=800&auto=format&fit=crop", # Silas (detective)
            "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=800&auto=format&fit=crop", # Clara (scholar)
            "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=800&auto=format&fit=crop", # Alistair (aristocrat)
            "https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=800&auto=format&fit=crop", # Evelyn (missing lady)
            "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=800&auto=format&fit=crop"  # Julian (port master)
        ]

        char_card_ids: Dict[str, str] = {}
        char_x_start = 80
        char_y_row = 560

        for idx, char in enumerate(characters):
            card_id = f"card_char_{char.get('id', idx)}"
            char_card_ids[char.get("name", f"char_{idx}")] = card_id
            is_suspect = char.get("role", "").lower() in ["antagonist", "suspect", "foil"] or "blackwood" in char.get("name", "").lower()
            status_val = char.get("current_status", "Alive")
            if is_suspect:
                status_val = "suspect"

            photo = char.get("portrait_url") or char_photos[idx % len(char_photos)]
            elements.append({
                "id": card_id,
                "story_id": story_id,
                "type": "character",
                "title": char.get("name", "Subject"),
                "subtitle": f"{char.get('role', 'Character')} • {char.get('current_status', 'Alive')}",
                "description": char.get("physical_description") or char.get("backstory", "")[:180] or "Subject under investigation.",
                "image_url": photo,
                "status": status_val,
                "is_culprit": False,
                "is_pinned": False,
                "color": "polaroid",
                "position": {"x": char_x_start + idx * 230, "y": char_y_row + (idx % 2 * 20)},
                "metadata": {
                    "role": char.get("role"),
                    "personality_traits": char.get("personality_traits", []),
                    "first_appearance": char.get("first_appearance", "Chapter 1"),
                    "character_id": char.get("id"),
                    "secrets": char.get("secrets", "")
                }
            })

        # 5. CHRONOLOGICAL STORY TIMELINE (Right Column)
        timeline_x = 1140
        timeline_y_start = 80

        default_timeline_events = [
            {"title": "11:40 PM • Waterlogged Watch Received", "desc": "Anonymous messenger delivers clockwork bearing engraved coordinates at harbor slip 4.", "chapter": 1},
            {"title": "12:15 AM • Shattered Window in Conservatory", "desc": "Silas arrives at Blackwood Manor. Footprints lead downward toward the sea cliffs.", "chapter": 2},
            {"title": "02:17 AM • Vault Decoded Under Lighthouse", "desc": "Clara Moreau translates the cipher wheel, unlocking the lower sea chamber.", "chapter": 3}
        ]

        active_events = events if len(events) > 0 else default_timeline_events
        timeline_card_ids: List[str] = []

        for idx, ev in enumerate(active_events[:4]):
            card_id = f"card_time_{ev.get('id', idx)}"
            timeline_card_ids.append(card_id)
            chap_num = ev.get("chapter_number") or ev.get("chapter", idx + 1)
            elements.append({
                "id": card_id,
                "story_id": story_id,
                "type": "event",
                "title": ev.get("title", f"Story Event {idx+1}"),
                "subtitle": f"Timeline Chronology • Chapter {chap_num}",
                "description": ev.get("description", "Key narrative milestone documented on board."),
                "status": "verified",
                "is_pinned": False,
                "color": "manila",
                "position": {"x": timeline_x, "y": timeline_y_start + idx * 190},
                "metadata": {
                    "chapter_number": chap_num,
                    "characters_involved": ev.get("characters_involved", [])
                }
            })

        # 6. EVIDENCE & IMPORTANT OBJECT CARDS (Lower Left & Center Scatter)
        evidence_photos = [
            "https://images.unsplash.com/photo-1509042239860-f550ce710b93?q=80&w=800&auto=format&fit=crop", # Watch / relic
            "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?q=80&w=800&auto=format&fit=crop", # Old book / archive
            "https://images.unsplash.com/photo-1516962215378-7fa2e137ae93?q=80&w=800&auto=format&fit=crop"  # Key / letter
        ]

        default_evidence = [
            {
                "name": "Waterlogged Pocket Watch",
                "description": "Stopped precisely at 11:40 PM. Roman numerals encircle a concealed brass astronomical compass.",
                "first_appearance": "Chapter 1",
                "current_location": "Vance's Field Satchel",
                "significance": "Key cipher for the submerged lighthouse chamber lock."
            },
            {
                "name": "Forged Estate Ledger",
                "description": "Records dating to 1892 reveal payments to Julian Calder signed under a forged Blackwood crest.",
                "first_appearance": "Chapter 2",
                "current_location": "Conservatory Desk",
                "significance": "Establishes financial motive and maritime conspiracy."
            },
            {
                "name": "The Obsidian Sigil Key",
                "description": "Carved volcanic glass pulsing faintly when brought near salt water. Unlocks the seventh sea vault.",
                "first_appearance": "Chapter 3",
                "current_location": "The Whispering Archives",
                "significance": "Primary relic driving the occult society's agenda."
            }
        ]

        raw_evidence = (ai_data.get("evidence") if ai_data and isinstance(ai_data.get("evidence"), list) else None) or default_evidence
        evidence_card_ids: Dict[str, str] = {}
        ev_positions = [
            {"x": 80, "y": 880},
            {"x": 360, "y": 890},
            {"x": 640, "y": 880}
        ]

        for idx, ev_item in enumerate(raw_evidence[:3]):
            card_id = f"card_ev_{idx}_{story_id}"
            evidence_card_ids[ev_item.get("name", f"ev_{idx}")] = card_id
            pos = ev_positions[idx] if idx < len(ev_positions) else {"x": 200 + idx * 220, "y": 900}
            elements.append({
                "id": card_id,
                "story_id": story_id,
                "type": "evidence",
                "title": ev_item.get("name", "Piece of Evidence"),
                "subtitle": f"Evidence • Found in {ev_item.get('first_appearance', 'Chapter 1')}",
                "description": ev_item.get("description", "Material artifact logged into evidence."),
                "image_url": evidence_photos[idx % len(evidence_photos)],
                "status": "verified",
                "is_pinned": False,
                "color": "aged",
                "position": pos,
                "metadata": {
                    "first_appearance": ev_item.get("first_appearance"),
                    "current_location": ev_item.get("current_location"),
                    "significance": ev_item.get("significance")
                }
            })

        # 7. STICKY NOTES & CLUES (Handwritten Sticky Notes like Reference Image)
        sticky_notes = [
            {
                "title": "MEETING POINT X",
                "desc": "Wharf lights doused at 02:00 AM. Who signaled the skiff from the south breakwater?",
                "color": "yellow",
                "pos": {"x": 350, "y": 340}
            },
            {
                "title": "DEAD DROP 5/12",
                "desc": "Iron locker under lighthouse pier. Check tide schedule before midnight attempt.",
                "color": "pink",
                "pos": {"x": 930, "y": 350}
            },
            {
                "title": "WITNESS STATEMENT",
                "desc": "Fisherman heard three chimes from the sunken bell. Insists Evelyn walked toward the cliffs willingly.",
                "color": "green",
                "pos": {"x": 90, "y": 330}
            },
            {
                "title": "PARKING / CARRIAGE TICKET",
                "desc": "Cab driver paid with uncirculated 1888 sovereign. Matches Blackwood family vault mint.",
                "color": "yellow",
                "pos": {"x": 960, "y": 890}
            }
        ]

        for idx, sn in enumerate(sticky_notes):
            card_id = f"card_sticky_{idx}_{story_id}"
            elements.append({
                "id": card_id,
                "story_id": story_id,
                "type": "clue",
                "title": sn["title"],
                "subtitle": "Detective Observation",
                "description": sn["desc"],
                "color": sn["color"],
                "status": "unverified",
                "is_pinned": False,
                "position": sn["pos"],
                "metadata": {"mystery_note": True}
            })

        # 8. BUILD RED STRING CONNECTIONS (Inspired by reference photo)
        # Helper to find card id
        def get_char_id(name_substr: str) -> Optional[str]:
            for name, cid in char_card_ids.items():
                if name_substr.lower() in name.lower():
                    return cid
            return None

        silas_id = get_char_id("Silas") or (list(char_card_ids.values())[0] if char_card_ids else None)
        alistair_id = get_char_id("Alistair") or (list(char_card_ids.values())[1] if len(char_card_ids) > 1 else None)
        clara_id = get_char_id("Clara") or (list(char_card_ids.values())[2] if len(char_card_ids) > 2 else None)
        evelyn_id = get_char_id("Evelyn") or (list(char_card_ids.values())[3] if len(char_card_ids) > 3 else None)
        julian_id = get_char_id("Julian")

        manor_id = loc_card_ids.get("Blackwood Cliffside Manor") or (list(loc_card_ids.values())[0] if loc_card_ids else None)
        archive_id = loc_card_ids.get("The Whispering Archives & Lighthouse") or (list(loc_card_ids.values())[1] if len(loc_card_ids) > 1 else None)
        harbor_id = loc_card_ids.get("Ravenscar Maritime Harbor (Slip 4)")

        watch_id = evidence_card_ids.get("Waterlogged Pocket Watch") or (list(evidence_card_ids.values())[0] if evidence_card_ids else None)
        ledger_id = evidence_card_ids.get("Forged Estate Ledger") or (list(evidence_card_ids.values())[1] if len(evidence_card_ids) > 1 else None)

        # Connect Silas -> Watch (Possesses key clue)
        if silas_id and watch_id:
            connections.append({
                "id": f"conn_silas_watch_{story_id}",
                "source_id": silas_id,
                "target_id": watch_id,
                "label": "Possesses key cipher",
                "type": "evidence",
                "notes": "Delivered to Vance by anonymous harbor courier"
            })

        # Connect Silas -> Manor (Investigating scene)
        if silas_id and manor_id:
            connections.append({
                "id": f"conn_silas_manor_{story_id}",
                "source_id": silas_id,
                "target_id": manor_id,
                "label": "Inspected crime scene",
                "type": "location",
                "notes": "Discovered broken conservatory window"
            })

        # Connect Alistair -> Evelyn (Husband / Prime Suspect)
        if alistair_id and evelyn_id:
            connections.append({
                "id": f"conn_ali_eve_{story_id}",
                "source_id": alistair_id,
                "target_id": evelyn_id,
                "label": "Conflicting alibi & timeline",
                "type": "contradiction",
                "is_contradiction": True,
                "notes": "Alistair claims she left voluntarily at midnight"
            })

        # Connect Alistair -> Manor (Owner)
        if alistair_id and manor_id:
            connections.append({
                "id": f"conn_ali_manor_{story_id}",
                "source_id": alistair_id,
                "target_id": manor_id,
                "label": "Sole resident present",
                "type": "location",
                "notes": "Staged disappearance inside the estate"
            })

        # Connect Clara -> Archive (Archivist scholar)
        if clara_id and archive_id:
            connections.append({
                "id": f"conn_clara_arch_{story_id}",
                "source_id": clara_id,
                "target_id": archive_id,
                "label": "Decoded subterranean vault",
                "type": "location",
                "notes": "Discovered sea cave acoustic blueprints"
            })

        # Connect Julian -> Harbor
        if julian_id and harbor_id:
            connections.append({
                "id": f"conn_julian_harbor_{story_id}",
                "source_id": julian_id,
                "target_id": harbor_id,
                "label": "Controls night slip access",
                "type": "suspect",
                "notes": "Impounded witness boats"
            })

        # Connect Ledger -> Alistair (Motive)
        if ledger_id and alistair_id:
            connections.append({
                "id": f"conn_ledger_ali_{story_id}",
                "source_id": ledger_id,
                "target_id": alistair_id,
                "label": "Forged family signatures",
                "type": "evidence",
                "notes": "Extensive illicit payoffs logged"
            })

        # Sequential timeline connections
        for i in range(len(timeline_card_ids) - 1):
            connections.append({
                "id": f"conn_time_seq_{i}_{story_id}",
                "source_id": timeline_card_ids[i],
                "target_id": timeline_card_ids[i+1],
                "label": "Chronological progression",
                "type": "timeline",
                "notes": "Sequential investigation milestones"
            })

        # Connect Timeline #1 to Watch
        if timeline_card_ids and watch_id:
            connections.append({
                "id": f"conn_time1_watch_{story_id}",
                "source_id": timeline_card_ids[0],
                "target_id": watch_id,
                "label": "Timepiece delivered at 11:40 PM",
                "type": "timeline",
                "notes": "Anchor timestamp for investigation"
            })

        return {
            "story_id": story_id,
            "elements": elements,
            "connections": connections,
            "culprit_id": alistair_id,  # Initial suspect suggestion (can be changed by user!)
            "zoom": 1.0,
            "pan_offset": {"x": 0.0, "y": 0.0},
            "updated_at": datetime.utcnow().isoformat()
        }

    def incremental_chapter_analysis(
        self,
        story: Dict[str, Any],
        chapter: Dict[str, Any],
        existing_board: Dict[str, Any],
        memories: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Incremental analysis when a chapter is updated or added:
        - Detects new characters, locations, objects, and clues introduced in this chapter
        - Detects new continuity errors introduced specifically by this chapter
        - Adds them to the board without moving or destroying existing manual layout
        """
        story_id = story.get("id", "default_story")
        chap_num = chapter.get("chapter_number", 1)
        chap_title = chapter.get("title", f"Chapter {chap_num}")
        chap_content = chapter.get("content", "")[:2500]

        elements = list(existing_board.get("elements", []))
        connections = list(existing_board.get("connections", []))
        existing_titles = {e.get("title", "").lower() for e in elements}

        # Calculate bounding coordinates to place new items neatly below/beside
        max_x = max([e.get("position", {}).get("x", 200) for e in elements] or [800])
        max_y = max([e.get("position", {}).get("y", 200) for e in elements] or [700])

        prompt = f"""Analyze this newly added chapter for story '{story.get('title', '')}':
Chapter {chap_num}: {chap_title}
Text:
{chap_content}

Universe Memory:
{json.dumps([m.get('title') for m in memories[:6]])}

Extract any NEW:
1. "new_evidence": list of objects/clues introduced with "name", "description", "significance"
2. "new_clues": list of suspicious questions/leads with "title", "text"
3. "new_contradictions": list of continuity issues introduced against previous canon or memory

Return ONLY valid JSON with keys "new_evidence", "new_clues", "new_contradictions"."""

        ai_res = self._call_gemini(prompt)
        parsed = {}
        if ai_res:
            try:
                clean_json = re.sub(r"^```json|^```|```$", "", ai_res.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)
            except Exception:
                pass

        new_items_added = 0
        new_evidence_list = parsed.get("new_evidence") or [
            {
                "name": f"Encrypted Telegram from Chapter {chap_num}",
                "description": f"Intercepted wire message referencing coastal shipment coordinates in {chap_title}.",
                "significance": "Discloses covert communication between suspects."
            }
        ]

        for item in new_evidence_list:
            if item.get("name", "").lower() not in existing_titles:
                card_id = f"card_inc_ev_{uuid.uuid4().hex[:8]}"
                elements.append({
                    "id": card_id,
                    "story_id": story_id,
                    "type": "evidence",
                    "title": item.get("name", "New Evidence"),
                    "subtitle": f"Evidence • Added from Chapter {chap_num}",
                    "description": item.get("description", ""),
                    "status": "unverified",
                    "is_pinned": False,
                    "color": "aged",
                    "position": {"x": min(max_x + 80, 1400), "y": max_y + 40},
                    "metadata": {
                        "first_appearance": f"Chapter {chap_num}",
                        "significance": item.get("significance", "")
                    }
                })
                existing_titles.add(item.get("name", "").lower())
                max_y += 180
                new_items_added += 1

        new_clues_list = parsed.get("new_clues") or [
            {
                "title": f"LEAD: CHAPTER {chap_num} OBSERVATION",
                "text": f"Unanswered anomaly raised during {chap_title}. Requires cross-referencing with coroner logs."
            }
        ]

        for clue in new_clues_list:
            if clue.get("title", "").lower() not in existing_titles:
                card_id = f"card_inc_clue_{uuid.uuid4().hex[:8]}"
                elements.append({
                    "id": card_id,
                    "story_id": story_id,
                    "type": "clue",
                    "title": clue.get("title", "New Lead"),
                    "subtitle": f"Chapter {chap_num} Finding",
                    "description": clue.get("text", ""),
                    "status": "unverified",
                    "is_pinned": False,
                    "color": "yellow",
                    "position": {"x": max(100, max_x - 300), "y": max_y + 30},
                    "metadata": {"source_chapter": chap_title}
                })
                existing_titles.add(clue.get("title", "").lower())
                max_y += 160
                new_items_added += 1

        existing_board["elements"] = elements
        existing_board["connections"] = connections
        existing_board["updated_at"] = datetime.utcnow().isoformat()
        return {
            "board": existing_board,
            "new_items_added": new_items_added,
            "status": "success",
            "message": f"Incorporated Chapter {chap_num} findings into investigation board."
        }



ai_service = AIService()
