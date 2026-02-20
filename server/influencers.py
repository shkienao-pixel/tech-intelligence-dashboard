# Top 100 tech/AI influencers on X — curated by follower count & relevance
TOP_TECH_INFLUENCERS = [
    # ── AI Researchers & Scientists ──────────────────────────────────────────
    "karpathy",        # Andrej Karpathy — ex-OpenAI, ex-Tesla
    "ylecun",          # Yann LeCun — Meta Chief AI Scientist
    "sama",            # Sam Altman — OpenAI CEO
    "demishassabis",   # Demis Hassabis — Google DeepMind CEO
    "jeffdean",        # Jeff Dean — Google Senior Fellow
    "drfeifei",        # Fei-Fei Li — Stanford AI Lab
    "AndrewYNg",       # Andrew Ng — DeepLearning.AI
    "GaryMarcus",      # Gary Marcus — AI critic & author
    "emollick",        # Ethan Mollick — Wharton AI researcher
    "fchollet",        # François Chollet — Keras creator
    "drjimfan",        # Jim Fan — NVIDIA Senior Research Scientist
    "soumithchintala",  # Soumith Chintala — PyTorch co-creator
    "ESYudkowsky",     # Eliezer Yudkowsky — AI Safety / MIRI
    "tegmark",         # Max Tegmark — MIT FLI
    "hardmaru",        # David Ha — ex Google Brain
    # ── Tech CEOs & Founders ─────────────────────────────────────────────────
    "elonmusk",        # Elon Musk — xAI, Tesla, SpaceX
    "JensenHuang",     # Jensen Huang — NVIDIA CEO
    "sundarpichai",    # Sundar Pichai — Google CEO
    "satyanadella",    # Satya Nadella — Microsoft CEO
    "amasad",          # Amjad Masad — Replit CEO
    "geohot",          # George Hotz — comma.ai / tinygrad
    "EMostaque",       # Emad Mostaque — ex-Stability AI
    "gdb",             # Greg Brockman — OpenAI President
    "naval",           # Naval Ravikant — AngelList
    "paulg",           # Paul Graham — Y Combinator
    "pmarca",          # Marc Andreessen — a16z
    "balajis",         # Balaji Srinivasan — ex-Coinbase CTO
    "levelsio",        # Pieter Levels — indie hacker
    "bentossell",      # Ben Tossell — Makerpad
    "simonw",          # Simon Willison — Datasette, Django
    # ── AI Companies (official) ───────────────────────────────────────────────
    "OpenAI",          # OpenAI
    "GoogleDeepMind",  # Google DeepMind
    "AnthropicAI",     # Anthropic
    "MetaAI",          # Meta AI
    "MistralAI",       # Mistral AI
    "huggingface",     # Hugging Face
    "xai",             # xAI (Grok)
    "perplexity_ai",   # Perplexity AI
    "LangChainAI",     # LangChain
    "deepseek_ai",     # DeepSeek
    "StabilityAI",     # Stability AI
    "cohere",          # Cohere
    "character_ai",    # Character.AI
    "replit",          # Replit
    "cursor_ai",       # Cursor
    "weights_biases",  # Weights & Biases
    "llama_index",     # LlamaIndex
    "NvidiaAI",        # NVIDIA AI
    "GoogleAI",        # Google AI
    "groqinc",         # Groq (fast inference)
    # ── ML Engineers & Practitioners ─────────────────────────────────────────
    "jeremyphoward",   # Jeremy Howard — fast.ai
    "rasbt",           # Sebastian Raschka — author / ML researcher
    "svpino",          # Santiago Valdarrama — ML engineer
    "goodside",        # Riley Goodside — Scale AI, prompt engineering
    "tunguz",          # Bojan Tunguz — Kaggle Grandmaster
    "marktenenholtz",  # Mark Tenenholtz — ML engineer
    "alexalbert__",    # Alex Albert — Anthropic
    "omarsar0",        # Omar Sanseviero — Hugging Face
    "swyx",            # swyx — Latent Space podcast
    "minchoi",         # Min Choi — AI community builder
    "TinaHuang1",      # Tina Huang — ML YouTuber
    "repligate",       # AI commentary aggregator
    "aisolopreneur",   # AI solopreneur community
    # ── AI Safety & Ethics ───────────────────────────────────────────────────
    "timnitGebru",     # Timnit Gebru — DAIR founder
    "mmitchell_ai",    # Margaret Mitchell — AI ethics
    "Miles_Brundage",  # Miles Brundage — AI policy researcher
    "pmddomingos",     # Pedro Domingos — ML author
    # ── Analysts & Investors ─────────────────────────────────────────────────
    "benedictevans",   # Benedict Evans — tech analyst
    "stratechery",     # Ben Thompson — Stratechery
    "SemiAnalysis",    # Dylan Patel — semiconductor analysis
    "a16z",            # Andreessen Horowitz
    "ycombinator",     # Y Combinator
    "martin_casado",   # Martin Casado — a16z
    "deedydas",        # Deedy Das — Menlo Ventures
    "sarah_guo",       # Sarah Guo — Conviction VC
    "polynoamial",     # Noam Brown — Meta FAIR
    "bindureddy",      # Bindi Reddy — AI investor
    # ── Tech Media & Journalism ───────────────────────────────────────────────
    "verge",           # The Verge
    "techreview",      # MIT Technology Review
    "arstechnica",     # Ars Technica
    "wired",           # Wired
    "TechCrunch",      # TechCrunch
    "TheRundownAI",    # The Rundown AI (newsletter)
    "MKBHD",           # Marques Brownlee
    "thcasey",         # Casey Newton — Platformer
    "MSFTResearch",    # Microsoft Research
    # ── AI Products & Infrastructure ─────────────────────────────────────────
    "runway",          # Runway ML — video generation
    "ElevenLabs_io",   # ElevenLabs — voice AI
    "pika_labs",       # Pika — video generation
    "togethercompute", # Together.ai — inference
    "modal_labs",      # Modal — serverless GPU
    "replicate",       # Replicate — model hosting
    "PyTorch",         # PyTorch official
    "ilyasut",         # Ilya Sutskever — SSI
    "cwolferesearch",  # Christopher Wolfe — ML research
    # ── Global AI Ecosystem ───────────────────────────────────────────────────
    "AlibabaGroup",    # Alibaba (Qwen models)
    "mistralai",       # Mistral (backup handle)
    "collinburns_ai",  # Collin Burns — AI researcher
    "divgarg",         # Div Garg — AI investor
    "aibreaking",      # AI breaking news aggregator
]

# Deduplicate while preserving order
seen = set()
TOP_TECH_INFLUENCERS = [
    x for x in TOP_TECH_INFLUENCERS
    if x.lower() not in seen and not seen.add(x.lower())
]
