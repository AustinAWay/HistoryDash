#!/usr/bin/env python3
"""Generate personalized FRQ questions for each student by week."""

import os
import re
from pathlib import Path

# ============================================================================
# AP HUMAN GEOGRAPHY QUESTION TEMPLATES
# ============================================================================

APHG_QUESTIONS = {
    4: {  # Unit 4: Cultural Patterns and Processes
        "frq1": {
            "title": "Cultural Diffusion and Language",
            "question": """## FRQ: Cultural Diffusion and Language

**Time: 15 minutes | 7 points**

The map below shows the distribution of Romance languages in Europe.

[Imagine a map showing Spanish, Portuguese, French, Italian, and Romanian distributions]

A. **Define** relocation diffusion and provide ONE example of how it contributed to the spread of Romance languages outside of Europe.
*(2 points)*

B. **Explain** how the concept of a lingua franca relates to the historical spread of Latin and its influence on modern Romance languages.
*(2 points)*

C. **Describe** ONE way that language can serve as a centripetal force AND ONE way it can serve as a centrifugal force within a country.
*(3 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (2 points):**
- 1 point: Correctly defines relocation diffusion (spread of an idea/trait through physical movement of people)
- 1 point: Provides valid example (Spanish to Latin America via colonization, Portuguese to Brazil, French to Quebec/Africa)

**Part B (2 points):**
- 1 point: Correctly explains lingua franca concept (common language used between groups with different native languages)
- 1 point: Connects to Latin as administrative/trade language of Roman Empire, influencing development of daughter languages

**Part C (3 points):**
- 1 point: Describes centripetal example (shared language unifies national identity, facilitates communication, strengthens cultural bonds)
- 1 point: Describes centrifugal example (minority languages marginalized, language-based discrimination, separatist movements)
- 1 point: Provides specific country/regional example for either force
"""
        },
        "frq2": {
            "title": "Religion and Cultural Landscape",
            "question": """## FRQ: Religion and Cultural Landscape

**Time: 15 minutes | 7 points**

A. **Identify** TWO ways that religion shapes the cultural landscape of a region.
*(2 points)*

B. **Explain** the difference between an ethnic religion and a universalizing religion, providing ONE example of each.
*(2 points)*

C. **Describe** how religious pilgrimage can affect BOTH the cultural landscape AND the economic development of a sacred site location. Use a specific example in your response.
*(3 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (2 points):**
- 1 point each for TWO valid ways religion shapes landscape:
  - Religious architecture (churches, mosques, temples, shrines)
  - Sacred spaces/sites
  - Cemeteries and burial practices
  - Land use restrictions (sacred groves, prohibited areas)
  - Street names, monuments, public art

**Part B (2 points):**
- 1 point: Ethnic religion explanation (tied to specific ethnic group/place, doesn't actively seek converts) + example (Hinduism, Judaism, Shinto)
- 1 point: Universalizing religion explanation (seeks converts worldwide, not tied to specific place) + example (Christianity, Islam, Buddhism)

**Part C (3 points):**
- 1 point: Cultural landscape impact (religious architecture, facilities for pilgrims, transformation of site)
- 1 point: Economic development impact (tourism revenue, jobs, infrastructure development, services)
- 1 point: Specific example with detail (Mecca, Vatican, Varanasi, Jerusalem, etc.)
"""
        }
    },
    5: {  # Unit 5: Political Patterns and Processes
        "frq1": {
            "title": "Boundary Types and Disputes",
            "question": """## FRQ: Boundary Types and Disputes

**Time: 15 minutes | 7 points**

The map below shows the border between India and Pakistan, including the Line of Control in Kashmir.

[Imagine a map showing India-Pakistan border and Kashmir region]

A. **Define** a superimposed boundary and explain why the India-Pakistan border can be considered an example of this boundary type.
*(2 points)*

B. **Identify** ONE type of boundary dispute and explain how it applies to the Kashmir conflict.
*(2 points)*

C. **Explain** how the Kashmir conflict demonstrates BOTH centrifugal forces AND irredentism.
*(3 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (2 points):**
- 1 point: Defines superimposed boundary (boundary forced on existing cultural landscape by outside authority)
- 1 point: Explains application (British colonial partition in 1947 drew borders without full consideration of religious/ethnic distributions)

**Part B (2 points):**
- 1 point: Identifies boundary dispute type (definitional, locational, operational, allocational)
- 1 point: Correctly applies to Kashmir (e.g., locational - where exactly the border should be; definitional - what the treaty means)

**Part C (3 points):**
- 1 point: Explains centrifugal force (religious division between Hindu India and Muslim Pakistan, violence, separatist movements)
- 1 point: Defines/explains irredentism (desire to annex territory with shared cultural/ethnic characteristics)
- 1 point: Applies irredentism to Kashmir (both nations claim region based on historical/cultural ties)
"""
        },
        "frq2": {
            "title": "Forms of Governance",
            "question": """## FRQ: Forms of Governance

**Time: 15 minutes | 7 points**

A. **Define** devolution and identify TWO forces that can lead to devolutionary pressures within a state.
*(3 points)*

B. **Compare** how a federal system and a unitary system of government differ in their approach to managing regional diversity.
*(2 points)*

C. **Explain** how ONE country has used autonomous regions or special administrative zones to address devolutionary pressures, and evaluate whether this approach has been successful.
*(2 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (3 points):**
- 1 point: Defines devolution (transfer of power from central government to regional/local governments)
- 2 points: Identifies TWO forces (ethnic nationalism, economic inequality, physical geography/distance, religious differences, historical grievances)

**Part B (2 points):**
- 1 point: Federal system explanation (power divided between central and regional governments, regions have constitutional authority)
- 1 point: Unitary system explanation (power concentrated in central government, regional governments derive power from center)

**Part C (2 points):**
- 1 point: Identifies specific example with accurate detail (Spain/Catalonia, UK/Scotland, China/Hong Kong, Russia/Chechnya)
- 1 point: Evaluates success with supporting reasoning
"""
        }
    },
    6: {  # Unit 6: Agriculture and Rural Land-Use Patterns
        "frq1": {
            "title": "Agricultural Regions and Food Production",
            "question": """## FRQ: Agricultural Regions and Food Production

**Time: 15 minutes | 7 points**

The map below shows major agricultural regions in the United States.

[Imagine a map showing corn belt, wheat belt, dairy regions, and cotton production areas]

A. **Define** the Von Thünen model and explain ONE assumption the model makes about agricultural land use.
*(2 points)*

B. **Explain** how transportation costs affect the location of dairy farming versus grain farming in the Von Thünen model.
*(2 points)*

C. **Describe** ONE reason why the Von Thünen model may not accurately predict modern agricultural patterns AND provide a specific example.
*(3 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (2 points):**
- 1 point: Correctly defines Von Thünen model (model showing rings of agricultural activity around a central market based on transportation costs and land rent)
- 1 point: Identifies valid assumption (isolated state, flat terrain, single market, uniform soil fertility, rational farmers maximizing profit)

**Part B (2 points):**
- 1 point: Explains dairy farming location (perishable products must be near market, high transportation costs per unit)
- 1 point: Explains grain farming location (less perishable, can be transported farther, lower transportation costs per unit)

**Part C (3 points):**
- 1 point: Identifies valid limitation (refrigeration, improved transportation, multiple markets, global trade, government subsidies, technology)
- 1 point: Explains why this affects the model
- 1 point: Provides specific example (California dairy shipped nationwide, Argentine beef to Europe, vertical farming in cities)
"""
        },
        "frq2": {
            "title": "Green Revolution and Agricultural Change",
            "question": """## FRQ: Green Revolution and Agricultural Change

**Time: 15 minutes | 7 points**

Read the following excerpt about agricultural change:

"The introduction of high-yield crop varieties, chemical fertilizers, and mechanized farming transformed agricultural production in many developing countries during the late 20th century."

A. **Define** the Green Revolution and identify ONE region where it had significant impact.
*(2 points)*

B. **Explain** TWO positive effects of the Green Revolution on food production in developing countries.
*(2 points)*

C. **Describe** TWO negative consequences of the Green Revolution, addressing both environmental AND social impacts.
*(3 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (2 points):**
- 1 point: Correctly defines Green Revolution (introduction of high-yield seeds, irrigation, fertilizers, and pesticides to increase agricultural production)
- 1 point: Identifies valid region (South Asia/India, Mexico, Philippines, parts of Africa, Latin America)

**Part B (2 points):**
- 1 point each for TWO valid positive effects: increased crop yields, reduced famine, lower food prices, improved food security, economic growth in rural areas, increased exports

**Part C (3 points):**
- 1 point: Environmental impact (soil degradation, water depletion, chemical runoff, loss of biodiversity, dependence on fossil fuels, monoculture vulnerability)
- 1 point: Social impact (displacement of small farmers, increased inequality, debt from input costs, loss of traditional farming knowledge, rural-to-urban migration)
- 1 point: Specific examples or detailed explanation of mechanisms
"""
        }
    },
    7: {  # Unit 7: Cities and Urban Land-Use
        "frq1": {
            "title": "Urban Models",
            "question": """## FRQ: Urban Models

**Time: 15 minutes | 7 points**

The diagram below shows the Burgess Concentric Zone Model.

[Imagine a diagram showing 5 concentric rings: CBD, Zone of Transition, Working-class Residential, Middle-class Residential, Commuter Zone]

A. **Identify** the zone where gentrification is most likely to occur and explain why this zone is particularly susceptible to this process.
*(2 points)*

B. **Explain** TWO limitations of the Concentric Zone Model when applied to cities in developing countries.
*(2 points)*

C. **Compare** the Concentric Zone Model to the Latin American City Model. Identify TWO significant differences in the spatial organization of social classes.
*(3 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (2 points):**
- 1 point: Identifies Zone of Transition (Zone 2)
- 1 point: Explains susceptibility (older housing stock, proximity to CBD, lower property values attract investment, displacement of low-income residents)

**Part B (2 points):**
- 1 point each for TWO valid limitations:
  - Model assumes single CBD (many developing cities have multiple centers)
  - Doesn't account for informal settlements/slums
  - Based on American/European industrial cities
  - Doesn't reflect colonial urban planning legacies
  - Transportation infrastructure differs

**Part C (3 points):**
- 1 point: Accurately describes Latin American City Model structure
- 2 points: Identifies TWO differences:
  - Elite residential along spine vs. in outer ring
  - Squatter settlements on periphery vs. zone of transition
  - Commercial spine extending from CBD
  - Zone of maturity vs. working-class zone
  - Disamenity zone concept
"""
        },
        "frq2": {
            "title": "Urban Sustainability",
            "question": """## FRQ: Urban Sustainability

**Time: 15 minutes | 7 points**

A. **Define** urban sprawl and identify TWO negative environmental consequences of this development pattern.
*(3 points)*

B. **Explain** how mixed-use development and public transportation can work together to create more sustainable cities.
*(2 points)*

C. **Describe** ONE smart growth or new urbanism strategy and explain how it addresses a specific urban challenge.
*(2 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (3 points):**
- 1 point: Defines urban sprawl (unrestricted growth of urban areas into surrounding rural land, typically low-density development)
- 2 points: Identifies TWO environmental consequences (habitat destruction, increased air pollution, water runoff/pollution, loss of agricultural land, increased energy consumption, heat island effect)

**Part B (2 points):**
- 1 point: Explains mixed-use development benefits (reduces need for transportation, creates walkable neighborhoods, concentrates demand)
- 1 point: Connects to public transportation (higher density supports transit viability, transit nodes anchor development, reduces car dependency)

**Part C (2 points):**
- 1 point: Identifies and describes strategy (greenbelts, urban growth boundaries, transit-oriented development, infill development, walkable neighborhoods)
- 1 point: Explains how it addresses specific challenge (congestion, pollution, sprawl, housing affordability, etc.)
"""
        }
    },
    8: {  # Unit 8: Industrial and Economic Development
        "frq1": {
            "title": "Economic Development Models",
            "question": """## FRQ: Economic Development Models

**Time: 15 minutes | 7 points**

The diagram below shows Rostow's Stages of Economic Growth model.

[Imagine a diagram showing: 1. Traditional Society, 2. Preconditions for Takeoff, 3. Takeoff, 4. Drive to Maturity, 5. Age of Mass Consumption]

A. **Describe** TWO characteristics of a country in Stage 3 (Takeoff) of Rostow's model.
*(2 points)*

B. **Explain** ONE major criticism of Rostow's model and how dependency theory offers an alternative explanation for global economic inequality.
*(3 points)*

C. **Identify** a country that has recently experienced rapid industrialization and explain how its development path both aligns with AND deviates from Rostow's model.
*(2 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (2 points):**
- 1 point each for TWO characteristics:
  - Rapid growth in limited number of industries
  - Increasing investment rate (10%+ of GDP)
  - Urbanization accelerates
  - New political/social institutions emerge
  - Technology adoption increases

**Part B (3 points):**
- 1 point: Valid criticism (assumes all countries follow same path, Eurocentric, ignores colonial legacies, ignores global economic structure)
- 1 point: Explains dependency theory (core exploits periphery, development of some requires underdevelopment of others)
- 1 point: Shows how dependency theory explains inequality differently than Rostow

**Part C (2 points):**
- 1 point: Identifies appropriate country (China, South Korea, Vietnam, India, Brazil) with accurate development characteristics
- 1 point: Explains both alignment (stages visible) AND deviation (compressed timeline, state intervention, export-orientation)
"""
        },
        "frq2": {
            "title": "Economic Sectors and Development",
            "question": """## FRQ: Economic Sectors and Development

**Time: 15 minutes | 7 points**

A. **Define** deindustrialization and explain why this process has occurred in many developed countries since the 1970s.
*(2 points)*

B. **Describe** how the growth of the quaternary and quinary sectors relates to the development of post-industrial economies.
*(2 points)*

C. **Explain** how a Special Economic Zone (SEZ) functions and analyze ONE benefit AND ONE drawback of SEZs for developing countries.
*(3 points)*
""",
            "rubric": """### Scoring Rubric (7 points total)

**Part A (2 points):**
- 1 point: Defines deindustrialization (decline of manufacturing sector as share of economy/employment)
- 1 point: Explains causes (globalization, outsourcing to lower-wage countries, automation, shift to service economy)

**Part B (2 points):**
- 1 point: Describes quaternary sector (information/knowledge economy, research, IT, finance)
- 1 point: Connects to post-industrial characteristics (service-dominated, innovation-based, high education requirements)

**Part C (3 points):**
- 1 point: Explains SEZ function (designated area with different economic regulations, tax incentives, reduced tariffs to attract foreign investment)
- 1 point: Identifies valid benefit (job creation, technology transfer, export growth, infrastructure development)
- 1 point: Identifies valid drawback (limited linkages to local economy, exploitation of workers, environmental degradation, economic dependence)
"""
        }
    }
}

# ============================================================================
# AP WORLD HISTORY QUESTION TEMPLATES
# ============================================================================

WORLD_HISTORY_SAQ = {
    "unit11": {  # Test Prep / Mixed Units
        "saq1": {
            "title": "Trade Networks and Cultural Exchange",
            "question": """## SAQ: Trade Networks and Cultural Exchange

**Time: 12 minutes | 3 points**

Answer all parts of the question that follows.

A. **Identify** ONE technological innovation that facilitated long-distance trade in Afro-Eurasia between 1200 and 1450.

B. **Explain** how the innovation you identified in Part A affected cultural exchange between different regions.

C. **Describe** ONE way that increased trade during this period contributed to the spread of disease.
""",
            "rubric": """### Scoring Rubric (3 points total)

**Part A (1 point):**
- Identifies valid innovation: compass, astrolabe, lateen sail, stern-post rudder, caravan technologies, ship designs (junks, dhows)

**Part B (1 point):**
- Explains cultural exchange connection: spread of religions along trade routes, diffusion of artistic styles, transfer of agricultural techniques, spread of languages, exchange of ideas/texts

**Part C (1 point):**
- Describes disease spread mechanism: increased human contact, movement along trade routes, rats on ships, Mongol/caravan transmission, Black Death spread via Silk Road
"""
        },
        "saq2": {
            "title": "Revolutions and Political Change",
            "question": """## SAQ: Revolutions and Political Change

**Time: 12 minutes | 3 points**

"The ideas of the Enlightenment spread across the Atlantic, inspiring movements for independence and political change in the Americas."

Using the passage above, answer all parts:

A. **Identify** ONE Enlightenment idea that influenced revolutionary movements in the Americas.

B. **Explain** how the idea you identified in Part A was applied differently in TWO American independence movements.

C. **Describe** ONE limit to the application of Enlightenment ideals in the post-revolutionary period.
""",
            "rubric": """### Scoring Rubric (3 points total)

**Part A (1 point):**
- Identifies valid Enlightenment idea: natural rights, popular sovereignty, social contract, separation of powers, individual liberty, consent of the governed

**Part B (1 point):**
- Compares application in TWO movements (American, Haitian, Latin American revolutions) with specific differences in how ideals were implemented or limited

**Part C (1 point):**
- Describes valid limitation: continued slavery, limited suffrage, exclusion of women, indigenous peoples' rights ignored, social hierarchies maintained, economic inequality persisted
"""
        }
    }
}

WORLD_HISTORY_DBQ = {
    "dbq1": {
        "title": "Imperialism and Resistance",
        "question": """## DBQ: Imperialism and Resistance (1750-1900)

**Time: 60 minutes (including 15-minute reading period) | 7 points**

**Evaluate the extent to which the responses to European imperialism in Africa and Asia were similar during the period 1750-1900.**

### Document 1
Letter from Qing Emperor Qianlong to King George III, 1793:
"Our Celestial Empire possesses all things in prolific abundance... There is therefore no need to import the manufactures of outside barbarians in exchange for our own produce."

### Document 2
Description of the Sepoy Rebellion, 1857 (British military report):
"The native soldiers have risen against their officers, motivated by both religious grievances and a desire to restore the Mughal Emperor to power."

### Document 3
Speech by Ethiopian Emperor Menelik II, 1893:
"I have no intention of being an indifferent spectator if the distant Powers hold onto the idea of dividing Africa... Ethiopia has been for fourteen centuries a Christian island in a sea of Pagans."

### Document 4
Excerpt from a Vietnamese scholar's memorial to the Emperor, 1867:
"If we resist, they will attack us more fiercely. If we surrender, they will only take more. Our only choice is to build our own strength through reform."

### Document 5
Account of the Zulu response to British expansion, 1879:
"King Cetshwayo organized his armies in the traditional manner, using superior numbers and knowledge of terrain to inflict a devastating defeat at Isandlwana."

### Document 6
Japanese Meiji government reform document, 1868:
"Knowledge shall be sought throughout the world, so as to strengthen the foundations of imperial rule... The evil customs of the past shall be broken off."

### Document 7
Egyptian nationalist newspaper article, 1882:
"We do not oppose progress or civilization. We oppose the occupation of our land and the control of our finances by foreign powers who claim to bring civilization but bring only exploitation."

---

In your response you should do the following:
- Respond to the prompt with a historically defensible thesis or claim that establishes a line of reasoning
- Describe a broader historical context relevant to the prompt
- Support your argument using at least six documents
- Use at least one additional piece of specific historical evidence beyond the documents
- For at least three documents, explain how the document's point of view, purpose, historical situation, and/or audience is relevant
- Demonstrate a complex understanding of the historical development
""",
        "rubric": """### DBQ Scoring Rubric (7 points total)

**A. THESIS/CLAIM (0-1 point)**
- 1 point: Responds to the prompt with a historically defensible thesis/claim that establishes a line of reasoning
- Must make a claim about the extent of similarity (fully similar, mostly similar, more different than similar, etc.) AND establish categories/reasoning

**B. CONTEXTUALIZATION (0-1 point)**
- 1 point: Describes a broader historical context relevant to the prompt
- Must connect to broader developments BEFORE or DURING the period (Industrial Revolution, earlier colonialism, decline of Asian empires, etc.)

**C. EVIDENCE (0-3 points)**

*Evidence from Documents (0-2 points):*
- 1 point: Uses content of at least THREE documents to address the topic
- 2 points: Uses at least SIX documents to support an argument

*Evidence Beyond Documents (0-1 point):*
- 1 point: Uses at least ONE piece of specific historical evidence beyond the documents to support or qualify the argument
- Examples: Boxer Rebellion, Indian National Congress, Berlin Conference, specific treaties, other resistance movements

**D. ANALYSIS AND REASONING (0-2 points)**

*Sourcing (0-1 point):*
- 1 point: For at least THREE documents, explains how document's point of view, purpose, historical situation, and/or audience is relevant to argument
- Must connect HIPP to the document's use in the argument, not just identify it

*Complexity (0-1 point):*
- 1 point: Demonstrates complex understanding through sophisticated argument
- Ways to achieve: analyzing multiple variables, explaining relevant similarities AND differences, explaining relevant connections across time/geography, qualifying or modifying argument, explaining nuance
"""
    }
}

WORLD_HISTORY_LEQ = {
    "leq1": {
        "title": "Causes of World War I",
        "question": """## LEQ: Causes of World War I

**Time: 40 minutes | 6 points**

**Evaluate the extent to which nationalism was responsible for the outbreak of World War I.**

In your response you should do the following:
- Respond to the prompt with a historically defensible thesis or claim that establishes a line of reasoning
- Describe a broader historical context relevant to the prompt
- Support an argument in response to the prompt using specific and relevant examples of evidence
- Use historical reasoning (causation, comparison, continuity and change) to frame or structure your argument
- Demonstrate a complex understanding of the historical development
""",
        "rubric": """### LEQ Scoring Rubric (6 points total)

**A. THESIS/CLAIM (0-1 point)**
- 1 point: Responds to the prompt with a historically defensible thesis that establishes a line of reasoning
- Must make a claim about the EXTENT to which nationalism was responsible (not just "nationalism caused WWI")
- Must set up an argument (e.g., "Nationalism was the primary cause because... however, other factors like...")

**B. CONTEXTUALIZATION (0-1 point)**
- 1 point: Describes a broader historical context relevant to the prompt
- Must be more than a phrase/reference - needs development
- Examples: Rise of nation-states in 19th century, unification of Germany/Italy, decline of empires, alliance systems, industrialization

**C. EVIDENCE (0-2 points)**
- 1 point: Provides specific examples relevant to the topic
- 2 points: Supports an argument using specific, relevant examples
- Evidence: Pan-Slavism, German nationalism, assassination of Franz Ferdinand, Balkan crises, arms race, colonial rivalries

**D. ANALYSIS AND REASONING (0-2 points)**
- 1 point: Uses historical reasoning to frame argument (causation, comparison, or continuity/change)
- 2 points: Demonstrates complex understanding through sophisticated argument
- Complexity: Multiple causes, counterarguments, nuance about "extent," connections across regions/time
"""
    }
}

# ============================================================================
# AP US HISTORY QUESTION TEMPLATES
# ============================================================================

APUSH_SAQ = {
    "period8": {  # 1890-1945
        "saq1": {
            "title": "Progressive Era Reforms",
            "question": """## SAQ: Progressive Era Reforms

**Time: 12 minutes | 3 points**

Answer all parts of the question that follows.

A. **Briefly describe** ONE political reform of the Progressive Era aimed at increasing democratic participation.

B. **Briefly explain** ONE way that Progressive reformers attempted to address the social problems caused by industrialization.

C. **Briefly explain** ONE limitation of Progressive Era reforms in addressing inequality in American society.
""",
            "rubric": """### Scoring Rubric (3 points total)

**Part A (1 point):**
- Describes valid political reform: direct election of senators (17th Amendment), initiative, referendum, recall, direct primaries, women's suffrage movement, secret ballot

**Part B (1 point):**
- Explains valid social reform: settlement houses (Hull House), child labor laws, workplace safety regulations, temperance/Prohibition, public health initiatives, housing reform, education reform

**Part C (1 point):**
- Explains valid limitation: racism/exclusion of African Americans, nativism toward immigrants, limited women's rights beyond suffrage, middle-class bias, continuation of economic inequality, segregation persisted
"""
        }
    },
    "period9": {  # 1945-1980
        "saq1": {
            "title": "Civil Rights Movement",
            "question": """## SAQ: Civil Rights Movement

**Time: 12 minutes | 3 points**

Answer all parts of the question that follows.

A. **Identify** ONE strategy used by civil rights activists in the 1950s-1960s to challenge segregation.

B. **Explain** how the strategy you identified in Part A reflected the broader philosophy of the civil rights movement.

C. **Describe** ONE way the federal government responded to civil rights activism during this period.
""",
            "rubric": """### Scoring Rubric (3 points total)

**Part A (1 point):**
- Identifies valid strategy: sit-ins, freedom rides, boycotts (Montgomery), marches, voter registration drives, litigation/court challenges, civil disobedience

**Part B (1 point):**
- Explains connection to philosophy: nonviolent direct action, moral witness, exposing injustice through media, building coalitions, appealing to conscience of nation, working within legal system

**Part C (1 point):**
- Describes federal response: Civil Rights Acts (1964, 1968), Voting Rights Act (1965), Brown v. Board enforcement, federal troops (Little Rock), creation of Civil Rights Commission, executive orders
"""
        }
    }
}

APUSH_DBQ = {
    "dbq1": {
        "title": "New Deal Effectiveness",
        "question": """## DBQ: New Deal Effectiveness

**Time: 60 minutes (including 15-minute reading period) | 7 points**

**Evaluate the extent to which the New Deal was effective in addressing the problems of the Great Depression.**

### Document 1
Excerpt from FDR's First Inaugural Address, March 1933:
"This Nation asks for action, and action now... We must act and act quickly."

### Document 2
Statistics from the Bureau of Labor Statistics:
Unemployment rates: 1933 - 24.9%, 1937 - 14.3%, 1939 - 17.2%

### Document 3
Letter from a farmer to Eleanor Roosevelt, 1936:
"The AAA payments helped us keep our farm when we would have lost everything. But my neighbor, a sharecropper, got nothing and had to leave."

### Document 4
Excerpt from Huey Long's "Share Our Wealth" speech, 1934:
"The New Deal does not go far enough. We need to redistribute wealth to every American family."

### Document 5
Business executive testimony to Congress, 1935:
"The NIRA has brought stability to our industry and ended cutthroat competition, but the costs of compliance are becoming burdensome."

### Document 6
African American newspaper editorial, 1935:
"While the CCC and WPA have provided jobs, discrimination means Black workers receive lower wages and are excluded from many programs."

### Document 7
Social Security Administration document, 1935:
"This act provides for old-age insurance, unemployment compensation, and aid to dependent children and the disabled."

---

In your response you should do the following:
- Respond to the prompt with a historically defensible thesis or claim that establishes a line of reasoning
- Describe a broader historical context relevant to the prompt
- Support your argument using at least six documents
- Use at least one additional piece of specific historical evidence beyond the documents
- For at least three documents, explain how the document's point of view, purpose, historical situation, and/or audience is relevant
- Demonstrate a complex understanding of the historical development
""",
        "rubric": """### DBQ Scoring Rubric (7 points total)

**A. THESIS/CLAIM (0-1 point)**
- 1 point: Responds to the prompt with a historically defensible thesis that establishes a line of reasoning
- Must address EXTENT of effectiveness (fully effective, partially effective, limited effectiveness, etc.)

**B. CONTEXTUALIZATION (0-1 point)**
- 1 point: Describes a broader historical context
- Examples: Causes of Great Depression, Hoover's response, previous progressive reforms, global depression

**C. EVIDENCE (0-3 points)**
- 1 point: Uses content of at least THREE documents
- 2 points: Uses at least SIX documents to support argument
- 1 point: Uses at least ONE piece of evidence beyond documents (court packing, specific agencies, WWII recovery)

**D. ANALYSIS AND REASONING (0-2 points)**
- 1 point: For THREE documents, explains HIPP (historical situation, intended audience, purpose, point of view)
- 1 point: Demonstrates complexity (multiple perspectives, limitations AND successes, continuity and change)
"""
    }
}

APUSH_LEQ = {
    "leq1": {
        "title": "American Imperialism",
        "question": """## LEQ: American Imperialism

**Time: 40 minutes | 6 points**

**Evaluate the extent to which United States foreign policy in the period 1890-1920 was a departure from earlier American foreign policy traditions.**

In your response you should do the following:
- Respond to the prompt with a historically defensible thesis or claim that establishes a line of reasoning
- Describe a broader historical context relevant to the prompt
- Support an argument in response to the prompt using specific and relevant examples of evidence
- Use historical reasoning (causation, comparison, continuity and change) to frame or structure your argument
- Demonstrate a complex understanding of the historical development
""",
        "rubric": """### LEQ Scoring Rubric (6 points total)

**A. THESIS/CLAIM (0-1 point)**
- 1 point: Makes claim about EXTENT of departure (complete break, significant departure, continuation with modifications, etc.)
- Must establish line of reasoning comparing to earlier policies

**B. CONTEXTUALIZATION (0-1 point)**
- 1 point: Broader historical context
- Examples: Monroe Doctrine, Manifest Destiny, isolationism, industrialization, closing of frontier, Social Darwinism

**C. EVIDENCE (0-2 points)**
- 1 point: Provides specific examples
- 2 points: Supports argument with specific examples
- Evidence: Spanish-American War, Philippines, Open Door Policy, Panama Canal, Roosevelt Corollary, Wilson's interventions

**D. ANALYSIS AND REASONING (0-2 points)**
- 1 point: Uses comparison/continuity and change to frame argument
- 2 points: Complex understanding (similarities AND differences, multiple factors, nuanced assessment of "extent")
"""
    }
}

# ============================================================================
# AP US GOVERNMENT QUESTION TEMPLATES
# ============================================================================

AP_GOV_QUESTIONS = {
    "concept_app": {
        "title": "Concept Application - Federalism",
        "question": """## Concept Application: Federalism

**Time: 20 minutes | 4 points**

Read the scenario below and answer the questions that follow.

**Scenario:** A state government passes legislation legalizing recreational marijuana use within its borders. However, marijuana remains classified as a Schedule I controlled substance under federal law. Federal law enforcement agencies continue to enforce federal drug laws within the state, leading to conflict between state and federal authorities.

A. **Describe** the constitutional principle of federalism as it relates to this scenario.
*(1 point)*

B. **Explain** how the Supremacy Clause (Article VI) applies to the conflict described in the scenario.
*(1 point)*

C. **Explain** how the Tenth Amendment might be used to argue in favor of the state's position.
*(1 point)*

D. **Describe** ONE way the federal government could respond to this conflict that does not involve direct enforcement.
*(1 point)*
""",
        "rubric": """### Scoring Rubric (4 points total)

**Part A (1 point):**
- Describes federalism as division of power between national and state governments
- Must connect to the scenario (shared/overlapping jurisdiction, conflict between levels)

**Part B (1 point):**
- Explains that federal law is "supreme law of the land"
- Applies to scenario: federal drug laws would theoretically take precedence over conflicting state laws

**Part C (1 point):**
- Explains Tenth Amendment reserves powers to states/people not delegated to federal government
- Applies argument: drug policy could be seen as reserved power; states' rights to regulate within borders

**Part D (1 point):**
- Valid federal responses: withholding federal funding, prosecutorial discretion (choosing not to enforce), seeking legislative compromise, court challenge
"""
    },
    "scotus": {
        "title": "SCOTUS Comparison - First Amendment",
        "question": """## SCOTUS Comparison: First Amendment

**Time: 20 minutes | 4 points**

**Required Case: Tinker v. Des Moines (1969)** - Students wore black armbands to school to protest the Vietnam War. The Supreme Court ruled that students do not "shed their constitutional rights to freedom of speech or expression at the schoolhouse gate."

**Non-Required Case Scenario:** A public high school student is suspended for posting inflammatory comments about school administrators on social media from home, outside of school hours. The student argues this violates their First Amendment rights.

A. **Identify** the constitutional provision that is common to both Tinker v. Des Moines and the non-required case scenario.
*(1 point)*

B. **Describe** the ruling in Tinker v. Des Moines and explain the standard the Court established.
*(1 point)*

C. **Explain** how the facts in the non-required case scenario are similar to OR different from the facts in Tinker.
*(1 point)*

D. **Explain** how the ruling in Tinker v. Des Moines could be applied to support the student's OR the school's position in the non-required case.
*(1 point)*
""",
        "rubric": """### Scoring Rubric (4 points total)

**Part A (1 point):**
- First Amendment / freedom of speech / freedom of expression

**Part B (1 point):**
- Ruling: Students have First Amendment rights in school
- Standard: Speech can only be restricted if it causes "substantial disruption" or interferes with rights of others

**Part C (1 point):**
- Similarities: Student speech, school punishment, protest/criticism element
- Differences: Location (off-campus vs on-campus), medium (social media vs physical protest), nature of speech (targeted criticism vs symbolic protest)

**Part D (1 point):**
- For student: Tinker protects speech unless substantially disruptive; off-campus speech entitled to more protection
- For school: Speech targeting administrators could cause disruption; schools have interest in maintaining order
"""
    },
    "argument": {
        "title": "Argument Essay - Electoral College",
        "question": """## Argument Essay: Electoral College

**Time: 40 minutes | 6 points**

Develop an argument that takes a position on whether the Electoral College should be maintained or replaced with a national popular vote for presidential elections.

In your essay, you must:
- Articulate a defensible claim or thesis that responds to the prompt
- Support your claim with at least TWO pieces of accurate and relevant evidence from the following foundational documents:
  - Federalist No. 68
  - Brutus No. 1
  - The Constitution (Article II, Section 1 and/or the 12th Amendment)
- Use reasoning to explain how your evidence supports your claim
- Respond to an opposing or alternate perspective

**Foundational Document Excerpts:**

**Federalist No. 68 (Hamilton):** "It was desirable that the sense of the people should operate in the choice of the person to whom so important a trust was to be confided... It was equally desirable, that the immediate election should be made by men most capable of analyzing the qualities adapted to the station."

**Brutus No. 1:** "In so extensive a republic, the great officers of government would soon become above the control of the people, and abuse their power."

**Constitution, Article II, Section 1:** "Each State shall appoint, in such Manner as the Legislature thereof may direct, a Number of Electors, equal to the whole Number of Senators and Representatives to which the State may be entitled in the Congress."
""",
        "rubric": """### Scoring Rubric (6 points total)

**Row 1: Thesis/Claim (0-1 point)**
- 1 point: Articulates a defensible claim or thesis that responds to the question and establishes a line of reasoning
- Must take a clear position and preview reasoning

**Row 2: Evidence (0-3 points)**
- 1 point: Provides TWO pieces of specific, relevant evidence from foundational documents
- 2 points: Uses evidence to support the argument (not just mention/describe)
- 3 points: Uses evidence from foundational documents AND course concepts to build a sophisticated argument

**Row 3: Reasoning (0-1 point)**
- 1 point: Explains how the evidence supports the thesis with logical reasoning
- Must connect evidence to claim, not just describe evidence

**Row 4: Response to Alternate Perspective (0-1 point)**
- 1 point: Responds to an opposing or alternate perspective
- Must address counterargument substantively, not just acknowledge it exists
"""
    },
    "quant_analysis": {
        "title": "Quantitative Analysis - Voter Turnout",
        "question": """## Quantitative Analysis: Voter Turnout

**Time: 20 minutes | 4 points**

Use the data in the table below to answer the questions.

**Voter Turnout in Presidential Elections by Age Group**

| Age Group | 2008 | 2012 | 2016 | 2020 |
|-----------|------|------|------|------|
| 18-29     | 51%  | 45%  | 46%  | 52%  |
| 30-44     | 62%  | 59%  | 58%  | 63%  |
| 45-64     | 69%  | 67%  | 66%  | 69%  |
| 65+       | 72%  | 70%  | 71%  | 74%  |
| Overall   | 64%  | 62%  | 61%  | 67%  |

A. **Identify** the age group with the highest voter turnout in 2020 and the age group with the lowest voter turnout.
*(1 point)*

B. **Describe** a pattern or trend in voter turnout shown in the data.
*(1 point)*

C. **Explain** ONE political consequence of the pattern you identified in Part B.
*(1 point)*

D. **Describe** ONE structural barrier that could explain lower voter turnout among young voters.
*(1 point)*
""",
        "rubric": """### Scoring Rubric (4 points total)

**Part A (1 point):**
- Correctly identifies: 65+ highest (74%), 18-29 lowest (52%)

**Part B (1 point):**
- Valid patterns: Older voters consistently have higher turnout; 2020 had highest overall turnout; turnout generally declined from 2008-2016 then increased; young voter turnout varies more

**Part C (1 point):**
- Valid consequences: Policies favor older voters (Social Security, Medicare protected); candidates appeal more to older voters; younger voters' issues (student loans, climate) get less attention; incumbents favored by higher-turnout demographics

**Part D (1 point):**
- Valid barriers: Voter registration requirements, ID laws, fewer polling places near colleges, work/school schedules, less residential stability, less political socialization, difficulty with absentee voting
"""
    }
}

# ============================================================================
# MODEL DRAWING EXERCISES
# ============================================================================

MODEL_EXERCISES = {
    "dtm": {
        "title": "Model Drawing: Demographic Transition Model",
        "question": """## Model Drawing Exercise: Demographic Transition Model (DTM)

**Time: 10 minutes**

**Instructions:**
On a blank piece of paper, draw the complete Demographic Transition Model from memory. Include everything you know about the model - structure, stages, trends, and characteristics.

**Do not look at any notes. Draw everything you can recall, then check your work.**
""",
        "rubric": """### Self-Check Rubric

**Structure (3 points):**
- [ ] Axes labeled correctly (time on x-axis, rates on y-axis)
- [ ] Five distinct stages shown and labeled
- [ ] Birth rate AND death rate lines clearly distinguished (two separate lines)

**Stage Accuracy (5 points - 1 per stage):**
- [ ] Stage 1: High birth rate, high death rate, low/stable population
- [ ] Stage 2: High birth rate, DECLINING death rate, rapid population growth
- [ ] Stage 3: DECLINING birth rate, low death rate, slowing growth
- [ ] Stage 4: Low birth rate, low death rate, stable population
- [ ] Stage 5: Very low birth rate, low death rate, potential population DECLINE

**Details (2 points):**
- [ ] Example countries/regions for each stage
- [ ] Reasons for transitions noted (industrialization, healthcare, urbanization, women's education)

**If you missed any elements, redraw the model focusing on those areas.**
"""
    },
    "burgess": {
        "title": "Model Drawing: Burgess Concentric Zone Model",
        "question": """## Model Drawing Exercise: Burgess Concentric Zone Model

**Time: 8 minutes**

**Instructions:**
On a blank piece of paper, draw the complete Burgess Concentric Zone Model from memory. Include all zones with their names, characteristics, and typical land uses.

**Do not look at any notes. Draw everything you can recall, then check your work.**
""",
        "rubric": """### Self-Check Rubric

**Structure (2 points):**
- [ ] Concentric ring structure (how many rings did you draw?)
- [ ] Central zone identified correctly

**Zone Labels (5 points - 1 per zone):**
- [ ] Zone 1: CBD (Central Business District) - commercial, offices, retail
- [ ] Zone 2: Zone of Transition - industry, deteriorating housing, immigrants, poverty
- [ ] Zone 3: Working-class residential - older housing, near factories
- [ ] Zone 4: Middle-class residential - newer housing, families, better conditions
- [ ] Zone 5: Commuter zone - suburbs, highest income, newest housing

**Application (3 points):**
- [ ] Can identify where gentrification occurs (Zone 2)
- [ ] Can explain bid-rent theory connection
- [ ] Can identify limitations of model (single CBD, American-centric, historical)

**If you missed any elements, redraw focusing on those areas.**
"""
    },
    "von_thunen": {
        "title": "Model Drawing: Von Thunen Model",
        "question": """## Model Drawing Exercise: Von Thunen Model

**Time: 8 minutes**

**Instructions:**
On a blank piece of paper, draw the complete Von Thunen Model of agricultural land use from memory. Include the spatial arrangement, what each zone produces, and why.

**Do not look at any notes. Draw everything you can recall, then check your work.**
""",
        "rubric": """### Self-Check Rubric

**Structure (2 points):**
- [ ] Concentric ring structure shown
- [ ] Central market/city identified

**Ring Labels (4 points):**
- [ ] Ring 1: Intensive farming / market gardening / dairy (perishable, high transport cost)
- [ ] Ring 2: Forest (heavy, needed for fuel/construction, before modern transport)
- [ ] Ring 3: Field crops / grains (less perishable, extensive agriculture)
- [ ] Ring 4: Ranching / livestock (requires most space, lowest land rent)

**Understanding (4 points):**
- [ ] Can explain role of transport costs in determining location
- [ ] Can explain bid-rent principle for agriculture
- [ ] Can identify modern modifications (refrigeration, highways change the rings)
- [ ] Can explain assumptions (isolated state, flat plain, single market)

**If you missed any elements, redraw focusing on those areas.**
"""
    },
    "rostow": {
        "title": "Model Drawing: Rostow's Stages of Economic Growth",
        "question": """## Model Drawing Exercise: Rostow's Stages of Economic Growth

**Time: 8 minutes**

**Instructions:**
On a blank piece of paper, draw/diagram Rostow's Stages of Economic Growth from memory. Include all stages, their names, key characteristics, and example countries if you can.

**Do not look at any notes. Draw everything you can recall, then check your work.**
""",
        "rubric": """### Self-Check Rubric

**Structure (2 points):**
- [ ] Correct number of stages shown (how many?)
- [ ] Clear progression/direction indicated

**Stage Labels (5 points - 1 per stage):**
- [ ] Stage 1: Traditional Society - subsistence agriculture, limited technology, rigid social structure
- [ ] Stage 2: Preconditions for Takeoff - infrastructure development, agricultural surplus, external influences
- [ ] Stage 3: Takeoff - rapid industrialization, growth in key sectors, 10%+ investment rate
- [ ] Stage 4: Drive to Maturity - diversified economy, technological innovation, sustained growth
- [ ] Stage 5: Age of High Mass Consumption - service sector dominance, consumer goods, high living standards

**Critical Thinking (3 points):**
- [ ] Can identify criticism of model (Eurocentric, assumes linear path)
- [ ] Can compare to dependency theory alternative
- [ ] Can identify countries that don't fit the model

**If you missed any elements, redraw focusing on those areas.**
"""
    }
}

# ============================================================================
# QUESTION GENERATION FUNCTIONS
# ============================================================================

def create_question_file(student_name, week_num, questions, course):
    """Create a question file for a student for a specific week."""

    # Clean student name for filename
    clean_name = student_name.lower().replace(" ", "_").replace("-", "_")
    filename = f"{clean_name}_week{week_num}.md"

    content = f"""# {student_name} | Week {week_num} Questions
**Course:** {course}

---

"""
    for i, q in enumerate(questions, 1):
        content += f"# Question {i}: {q['title']}\n\n"
        content += q['question']
        content += """

---

<details markdown="1">
<summary style="font-size: 1.5em; font-weight: bold;">

⚠️ SCORING RUBRIC - NO SPOILERS ⚠️

Click to expand ONLY after completing your response.

</summary>

"""
        content += """
---
---
---
STOP - Have you finished writing your answer?
---
---
---

"""
        content += q['rubric']
        content += "\n\n</details>\n\n---\n\n"

    return filename, content


def generate_aphg_questions(student_name, focus_units, num_weeks):
    """Generate APHG questions for a student."""
    questions_by_week = []

    # Cycle through focus units and question types
    unit_idx = 0
    for week in range(1, num_weeks + 1):
        if not focus_units:
            continue

        unit = focus_units[unit_idx % len(focus_units)]

        if unit in APHG_QUESTIONS:
            # Alternate between frq1 and frq2
            frq_key = "frq1" if week % 2 == 1 else "frq2"
            if frq_key in APHG_QUESTIONS[unit]:
                q = APHG_QUESTIONS[unit][frq_key]
                questions_by_week.append({
                    'week': week,
                    'questions': [q],
                    'unit': unit
                })

        unit_idx += 1

    return questions_by_week


def generate_world_questions(student_name, focus_units, num_weeks):
    """Generate AP World History questions for a student."""
    questions_by_week = []

    saqs = list(WORLD_HISTORY_SAQ.get("unit11", {}).values())
    leqs = list(WORLD_HISTORY_LEQ.values())

    for week in range(1, num_weeks + 1):
        week_questions = []

        # Add SAQ each week
        saq_idx = (week - 1) % len(saqs) if saqs else 0
        if saqs:
            week_questions.append(saqs[saq_idx])

        # Add DBQ every 3 weeks
        if week % 3 == 0 and WORLD_HISTORY_DBQ:
            week_questions.append(WORLD_HISTORY_DBQ["dbq1"])

        # Add LEQ on weeks 2, 5 (alternating with DBQ)
        if week % 3 == 2 and leqs:
            leq_idx = ((week - 2) // 3) % len(leqs)
            week_questions.append(leqs[leq_idx])

        if week_questions:
            questions_by_week.append({
                'week': week,
                'questions': week_questions,
                'unit': 'Mixed'
            })

    return questions_by_week


def generate_apush_questions(student_name, focus_units, num_weeks):
    """Generate APUSH questions for a student."""
    questions_by_week = []

    all_saqs = []
    for period, qs in APUSH_SAQ.items():
        all_saqs.extend(qs.values())
    dbqs = list(APUSH_DBQ.values())
    leqs = list(APUSH_LEQ.values())

    for week in range(1, num_weeks + 1):
        week_questions = []

        # Add SAQ each week
        if all_saqs:
            saq_idx = (week - 1) % len(all_saqs)
            week_questions.append(all_saqs[saq_idx])

        # Add DBQ on even weeks for multi-week students
        if num_weeks > 1 and week % 2 == 0 and dbqs:
            dbq_idx = ((week - 2) // 2) % len(dbqs)
            week_questions.append(dbqs[dbq_idx])

        # Add LEQ on odd weeks after week 1 for multi-week students
        if num_weeks > 1 and week > 1 and week % 2 == 1 and leqs:
            leq_idx = ((week - 3) // 2) % len(leqs)
            week_questions.append(leqs[leq_idx])

        if week_questions:
            questions_by_week.append({
                'week': week,
                'questions': week_questions,
                'unit': 'Mixed'
            })

    return questions_by_week


def generate_gov_questions(student_name, focus_units, num_weeks):
    """Generate AP US Government questions for a student."""
    questions_by_week = []

    gov_qs = list(AP_GOV_QUESTIONS.values())

    for week in range(1, num_weeks + 1):
        week_questions = []

        q_idx = (week - 1) % len(gov_qs) if gov_qs else 0
        if gov_qs:
            week_questions.append(gov_qs[q_idx])

        if week_questions:
            questions_by_week.append({
                'week': week,
                'questions': week_questions,
                'unit': 'Gov'
            })

    return questions_by_week


def parse_student_plan(filepath):
    """Extract key info from a student plan."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract name and course
    title_match = re.search(r'^# (.+?) \| (.+)$', content, re.MULTILINE)
    if not title_match:
        return None

    name = title_match.group(1)
    course = title_match.group(2)

    # Extract focus units
    focus_match = re.search(r'\*\*Your focus units:\*\* (.+)', content)
    focus_str = focus_match.group(1) if focus_match else ''
    focus_units = [int(u.strip()) for u in focus_str.split(',') if u.strip().isdigit()]

    # If no focus units, find AMBER/RED units from table
    if not focus_units:
        amber_red = re.findall(r'\| (\d+) \|.+?\| (AMBER|RED) \|', content)
        focus_units = [int(u) for u, _ in amber_red if int(u) > 1]  # Skip intro units

    # Filter to units that have questions in the bank (APHG: 4,5,6,7,8)
    if 'Geography' in course:
        valid_units = [4, 5, 6, 7, 8]
        focus_units = [u for u in focus_units if u in valid_units]
        if not focus_units:
            focus_units = [4, 5, 6, 7, 8]  # Default for general review
    elif 'World' in course or 'US History' in course:
        if not focus_units:
            focus_units = [4, 5, 6, 7]
    elif 'Government' in course:
        if not focus_units:
            focus_units = [2, 3, 4, 5]

    # Count coaching calls
    call_count = len(re.findall(r'\| \d+ \| .+? \| \d{2}:\d{2} \|', content))

    return {
        'name': name,
        'course': course,
        'focus_units': focus_units,
        'num_calls': call_count
    }


def main():
    plans_dir = Path('student_plans_v3')
    questions_dir = plans_dir / 'questions'
    questions_dir.mkdir(exist_ok=True)

    print("Generating personalized FRQ questions...")

    for md_file in sorted(plans_dir.glob('*.md')):
        if md_file.name in ['MASTER_COACHING_SCHEDULE.md', 'TEMPLATE_Sydney_Barba.md', 'COACH_CALL_SUMMARY.md']:
            continue

        student = parse_student_plan(md_file)
        if not student or student['num_calls'] == 0:
            continue

        name = student['name']
        course = student['course']
        focus = student['focus_units']
        num_weeks = student['num_calls']

        # Generate questions based on course
        if 'Human Geography' in course:
            week_questions = generate_aphg_questions(name, focus, num_weeks)
            # Add model exercises for APHG students
            model_exercises = list(MODEL_EXERCISES.values())
            for wq in week_questions:
                model_idx = (wq['week'] - 1) % len(model_exercises)
                wq['questions'].append(model_exercises[model_idx])
        elif 'World History' in course:
            week_questions = generate_world_questions(name, focus, num_weeks)
        elif 'US History' in course:
            week_questions = generate_apush_questions(name, focus, num_weeks)
        elif 'Government' in course:
            week_questions = generate_gov_questions(name, focus, num_weeks)
        else:
            continue

        # Create question files
        for wq in week_questions:
            filename, content = create_question_file(
                name, wq['week'], wq['questions'], course
            )
            filepath = questions_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"  Created: {filename}")

    print(f"\nDone! Questions saved to {questions_dir}")


if __name__ == '__main__':
    main()
