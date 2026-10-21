# Changelog

## [0.5.1](https://github.com/Frontier-Legal/casebench/compare/v0.5.0...v0.5.1) (2026-10-21)


### Bug Fixes

* **workbench:** setup and History use shadcn's own components, and the model catalog loads once, in the background ([#104](https://github.com/Frontier-Legal/casebench/issues/104)) ([f42f145](https://github.com/Frontier-Legal/casebench/commit/f42f145d9813481961a2efe4469c4b116d6746e7))

## [0.5.0](https://github.com/Frontier-Legal/casebench/compare/v0.4.0...v0.5.0) (2026-10-20)


### Features

* setup starts in the workbench, with a guide, Home, and Jurisdictions and Models pages ([#99](https://github.com/Frontier-Legal/casebench/issues/99)) ([e19c497](https://github.com/Frontier-Legal/casebench/commit/e19c49727d45647af4746cea78fcf7399df25cc9))
* **team:** one server keeps many organisations apart, with Postgres row-level security ([#103](https://github.com/Frontier-Legal/casebench/issues/103)) ([ab2ccdf](https://github.com/Frontier-Legal/casebench/commit/ab2ccdf5817ed6f7d11ff92cd6423781b636813a))
* **workbench:** a History page charts each metric and error rate of a suite run by run ([#102](https://github.com/Frontier-Legal/casebench/issues/102)) ([eb60f98](https://github.com/Frontier-Legal/casebench/commit/eb60f9893cfa147681c74dce6ea48aa617793ec7))


### Documentation

* **decisions:** one shared cloud for every organisation, and run history charted from nightly CI runs (0066, 0067) ([#100](https://github.com/Frontier-Legal/casebench/issues/100)) ([bdb9e0d](https://github.com/Frontier-Legal/casebench/commit/bdb9e0da773c178b693449c7d37046341f011459))

## [0.4.0](https://github.com/Frontier-Legal/casebench/compare/v0.3.0...v0.4.0) (2026-10-16)


### Features

* **setup:** init asks whether lawyers review on a team server and names it, check reaches it with the engineer's key, and push says where a server comes from ([#88](https://github.com/Frontier-Legal/casebench/issues/88)) ([6edb222](https://github.com/Frontier-Legal/casebench/commit/6edb2229d5545dc7a93a0b9f8ef9db40d9948a3e))
* **workbench:** a Settings page that shows what each part is for and costs and edits every setting, and a Run page that starts and follows casebench run ([#89](https://github.com/Frontier-Legal/casebench/issues/89)) ([65c5012](https://github.com/Frontier-Legal/casebench/commit/65c50120035eaa20aef2b7eb3844e042d4ec53a2))

## [0.3.0](https://github.com/Frontier-Legal/casebench/compare/v0.2.0...v0.3.0) (2026-10-16)


### Features

* a demo with no key, a first run that builds its suite, a setup skill, and answers from a closed tool ([#82](https://github.com/Frontier-Legal/casebench/issues/82)) ([7f1381d](https://github.com/Frontier-Legal/casebench/commit/7f1381df2bface3c43a2df44780c2fb9f1c5205c))
* **cloud:** casebench push, invite and pull: runs reach lawyers on the team server, and their decisions come back to CI ([#81](https://github.com/Frontier-Legal/casebench/issues/81)) ([93d7dd8](https://github.com/Frontier-Legal/casebench/commit/93d7dd890ee8de2984812138a34846ad165c9ffe))
* **team:** a seat check before invitations and erasing a team, the two seams a hosted service builds on ([#83](https://github.com/Frontier-Legal/casebench/issues/83)) ([ac7fe18](https://github.com/Frontier-Legal/casebench/commit/ac7fe181aeeb093b0f9d19ea6cfc56a03b4c7ff2))
* **team:** the team server: sign-in without IT, five roles, an audit log nothing changes, and one image ([#80](https://github.com/Frontier-Legal/casebench/issues/80)) ([7f0c1c5](https://github.com/Frontier-Legal/casebench/commit/7f0c1c5d43886c293815645a8b0f77bb6b9d3c25))
* **workbench:** every route checks what the caller may do, the event log is append-only, and a team build can add its screens ([#79](https://github.com/Frontier-Legal/casebench/issues/79)) ([afda3f4](https://github.com/Frontier-Legal/casebench/commit/afda3f42f2f5bfb3bd6fa39885a68acedd83f3fc))


### Bug Fixes

* **formats:** record the schemas 0.2.0 released, so they never change ([#77](https://github.com/Frontier-Legal/casebench/issues/77)) ([a4b2c22](https://github.com/Frontier-Legal/casebench/commit/a4b2c22a213380b80ffc3ce2c48340025a43ca25))

## [0.2.0](https://github.com/Frontier-Legal/casebench/compare/v0.1.1...v0.2.0) (2026-10-15)


### ⚠ BREAKING CHANGES

* a run, check, extract or case command now refuses every host casebench.yaml does not name. A setup whose agent calls a model API or another service that the config does not name stops at the first such call; add the host under `network: allow:`.

### Features

* a run calls only the hosts its config names, never follows a redirect to another host, and writes no key ([#60](https://github.com/Frontier-Legal/casebench/issues/60)) ([4a1a8c1](https://github.com/Frontier-Legal/casebench/commit/4a1a8c1a4610c42ed575ba3cdb5dc6525b5cbd4c))
* **cases:** lawyers write cases in a spreadsheet, and research, drafting, editing and extraction tasks are graded ([#66](https://github.com/Frontier-Legal/casebench/issues/66)) ([92e6383](https://github.com/Frontier-Legal/casebench/commit/92e6383f486814c7752af55a70dbc3e1aa56e582))
* **gate:** a gate fails a build only on a significant drop against a saved baseline, in pytest and a GitHub Action ([#64](https://github.com/Frontier-Legal/casebench/issues/64)) ([31a9289](https://github.com/Frontier-Legal/casebench/commit/31a9289e101682a3771c1c1b51fc162dce6abe38))
* **judge:** a verdict rests on a quote the answer holds and on the case's evidence, and lawyers' verdicts calibrate the judge ([#63](https://github.com/Frontier-Legal/casebench/issues/63)) ([e00459c](https://github.com/Frontier-Legal/casebench/commit/e00459c51e1cb49cd875e81e231fdcd548ed1a94))
* **report:** a run reports four error rates, each opening its failing answers, and a case names its practice area and approver ([#71](https://github.com/Frontier-Legal/casebench/issues/71)) ([5859549](https://github.com/Frontier-Legal/casebench/commit/585954994b4199b716a89c5e4f728c2d6c5df6e5))
* **report:** a run reports what it spent, per model, for the agent and for the judge ([#68](https://github.com/Frontier-Legal/casebench/issues/68)) ([2699c16](https://github.com/Frontier-Legal/casebench/commit/2699c165eaf881effb4b46419c04b33b1fb76660))
* **report:** a run's report exports for partners as PDF, Word or one HTML file that opens with no server ([#73](https://github.com/Frontier-Legal/casebench/issues/73)) ([fa0e2bd](https://github.com/Frontier-Legal/casebench/commit/fa0e2bdbfaca0e675dc260d6afdb33917acf2138))
* **review:** lawyers review a run in a spreadsheet, and the import writes the same verdicts the workbench writes ([#74](https://github.com/Frontier-Legal/casebench/issues/74)) ([b177153](https://github.com/Frontier-Legal/casebench/commit/b177153c2fa7c4909cab0c5cd89f1ab59efa02ef))
* **workbench:** a lawyer's change to golden data takes effect at once unless a second editor's approval is on ([#70](https://github.com/Frontier-Legal/casebench/issues/70)) ([628a906](https://github.com/Frontier-Legal/casebench/commit/628a9061473a5b05f08e101f95cc74259f36a773))
* **workbench:** engineers see each answer's harness as a waterfall, with unaccounted time, the authority funnel and a diff against another run ([#75](https://github.com/Frontier-Legal/casebench/issues/75)) ([9b179f6](https://github.com/Frontier-Legal/casebench/commit/9b179f604a857177912e10b7a1a9cd46b55c9950))
* **workbench:** golden data changes only when a second editor approves, and a question can be tried within a daily dollar limit ([#69](https://github.com/Frontier-Legal/casebench/issues/69)) ([1428607](https://github.com/Frontier-Legal/casebench/commit/142860736bd667296f454f5042e7bfeec4d3dd90))
* **workbench:** lawyers compare two runs of one suite blind, with a reason, summed per practice area ([#72](https://github.com/Frontier-Legal/casebench/issues/72)) ([a15560c](https://github.com/Frontier-Legal/casebench/commit/a15560cd1c71f40031fbc8c646690d8f88f77654))
* **workbench:** the review queue, where lawyers confirm or overrule the judge and approve court drafts ([#67](https://github.com/Frontier-Legal/casebench/issues/67)) ([58c5165](https://github.com/Frontier-Legal/casebench/commit/58c51659ec9c9a218b3fcd49b9c0d68fc46a3121))


### Bug Fixes

* **formats:** record the schemas 0.1.0 released, so they never change ([#62](https://github.com/Frontier-Legal/casebench/issues/62)) ([b6abfd8](https://github.com/Frontier-Legal/casebench/commit/b6abfd81aff331e3d90b9bc1ba42d08661ef0117))
* **gate:** the gate compares the scores the report shows, and names failed criteria by kind ([#65](https://github.com/Frontier-Legal/casebench/issues/65)) ([df326ae](https://github.com/Frontier-Legal/casebench/commit/df326ae778525ec9353dfa583d3b0fd211ae54b8))

## [0.1.1](https://github.com/Frontier-Legal/casebench/compare/v0.1.0...v0.1.1) (2026-10-14)


### Bug Fixes

* **docs:** the README sets Casebench up from PyPI ([#58](https://github.com/Frontier-Legal/casebench/issues/58)) ([5febc1f](https://github.com/Frontier-Legal/casebench/commit/5febc1f37a21c7ef50c58addbc77996cac3023a7))

## 0.1.0 (2026-10-14)


### ⚠ BREAKING CHANGES

* the adapters plugin kind and casebench.adapters are gone; Target.answer no longer takes a citation parser; corpus configs no longer take adapter_source.

### Features

* **capture:** receive OpenTelemetry spans a harness already emits ([#12](https://github.com/Frontier-Legal/casebench/issues/12)) ([254e552](https://github.com/Frontier-Legal/casebench/commit/254e5526b12f8ab4218edd33d029a47b42525712))
* **capture:** record model and backend calls through a local proxy ([#8](https://github.com/Frontier-Legal/casebench/issues/8)) ([aff784c](https://github.com/Frontier-Legal/casebench/commit/aff784c017a1095ff12eb9de526237695119bbf2))
* **capture:** record steps from functions the config names ([#11](https://github.com/Frontier-Legal/casebench/issues/11)) ([c8b0b9f](https://github.com/Frontier-Legal/casebench/commit/c8b0b9f5bd09b806671232854f4716027b065447))
* **cases:** write one case from a decision found by topic, or by hand, and approve it ([98cdf86](https://github.com/Frontier-Legal/casebench/commit/98cdf86f16fca5f9d25c19d2df4a8acc59b621d6))
* **core:** add the evaluation case model, frozen suites and score sets ([#4](https://github.com/Frontier-Legal/casebench/issues/4)) ([2f04d10](https://github.com/Frontier-Legal/casebench/commit/2f04d10bcd46a84712f877c6544eb6fb71fcf213))
* **corpus:** add any document store from the command line, check it and cache it ([#15](https://github.com/Frontier-Legal/casebench/issues/15)) ([8283a0b](https://github.com/Frontier-Legal/casebench/commit/8283a0b032e9864071b2474d1657d7bcd2e2ab73))
* **corpus:** connect several named corpora, with qualified ids and jurisdiction codes ([#32](https://github.com/Frontier-Legal/casebench/issues/32)) ([1776aa9](https://github.com/Frontier-Legal/casebench/commit/1776aa9a0e35cf639a2400f617a2b41011d44483))
* **corpus:** keep on disk only what a provider's terms allow ([98cdf86](https://github.com/Frontier-Legal/casebench/commit/98cdf86f16fca5f9d25c19d2df4a8acc59b621d6))
* **corpus:** pay a metered provider once per search ([#35](https://github.com/Frontier-Legal/casebench/issues/35)) ([db54f8f](https://github.com/Frontier-Legal/casebench/commit/db54f8fb4516d56c9790313696d4866e1198a3d2))
* **corpus:** set up the corpus from a data provider's profile, and offer bundled profiles in init ([#30](https://github.com/Frontier-Legal/casebench/issues/30)) ([54b3915](https://github.com/Frontier-Legal/casebench/commit/54b391511989238efcbc9aba9c55471562ff398f))
* **extract:** pass model settings to every provider and measure agreement, time and cost per setting ([98cdf86](https://github.com/Frontier-Legal/casebench/commit/98cdf86f16fca5f9d25c19d2df4a8acc59b621d6))
* **extract:** read answer keys out of court decisions with two models ([#17](https://github.com/Frontier-Legal/casebench/issues/17)) ([b12a1bd](https://github.com/Frontier-Legal/casebench/commit/b12a1bde3932cb845f9bd57a0dd8d01ca3882c6d))
* **formats:** version cases, suites, reports and corpus documents with JSON Schemas ([#29](https://github.com/Frontier-Legal/casebench/issues/29)) ([023ccdc](https://github.com/Frontier-Legal/casebench/commit/023ccdcd66731eaed89a9a1014d51b73f49df78b))
* **metrics:** a second judge from another family must agree before a citation passes ([#37](https://github.com/Frontier-Legal/casebench/issues/37)) ([3438b24](https://github.com/Frontier-Legal/casebench/commit/3438b24fb5d6a42244100446162632a0d58a6c93))
* **metrics:** check every citation against the corpus with the judge ([#16](https://github.com/Frontier-Legal/casebench/issues/16)) ([b79ec52](https://github.com/Frontier-Legal/casebench/commit/b79ec521e5df750fb371f914f4db392a0f31a62d))
* **metrics:** grade criteria with the judge and report the share of answers that pass them all ([#38](https://github.com/Frontier-Legal/casebench/issues/38)) ([8f14f95](https://github.com/Frontier-Legal/casebench/commit/8f14f9561b383067640460e749013747f8c76e8f))
* **metrics:** match citations by the corpus's description and finish scoring a real run ([#39](https://github.com/Frontier-Legal/casebench/issues/39)) ([b67dede](https://github.com/Frontier-Legal/casebench/commit/b67dede3339793d8d8c9dfdf113ac78dd5af74ba))
* **metrics:** route each citation to the corpora for its jurisdiction, and report per jurisdiction ([#33](https://github.com/Frontier-Legal/casebench/issues/33)) ([486f841](https://github.com/Frontier-Legal/casebench/commit/486f841451fbb5771bd90810765da43ae155445f))
* **plugins:** discover, scaffold and test plugins of every kind ([#5](https://github.com/Frontier-Legal/casebench/issues/5)) ([48dbcd4](https://github.com/Frontier-Legal/casebench/commit/48dbcd4b08b3a8761a7462e8ffc2d8dfe2588f75))
* **report:** every score set says what produced it, and compare names what differs ([#36](https://github.com/Frontier-Legal/casebench/issues/36)) ([7d08123](https://github.com/Frontier-Legal/casebench/commit/7d0812311cc7dec79149f4df6851f058352eeda1))
* **report:** follow each court authority through the captured steps ([#21](https://github.com/Frontier-Legal/casebench/issues/21)) ([b963e50](https://github.com/Frontier-Legal/casebench/commit/b963e50d04b64d32b288c43293fd10b196412f3b))
* **report:** say that citation checks wait for a corpus when a run was scored without one ([98cdf86](https://github.com/Frontier-Legal/casebench/commit/98cdf86f16fca5f9d25c19d2df4a8acc59b621d6))
* **report:** score each run with intervals and baselines, and compare runs ([#18](https://github.com/Frontier-Legal/casebench/issues/18)) ([08330fa](https://github.com/Frontier-Legal/casebench/commit/08330fa5af7dc6cb055f4ecb81442a5e3de29ceb))
* **run:** run a Python agent in worker processes with its calls captured ([#9](https://github.com/Frontier-Legal/casebench/issues/9)) ([98b980e](https://github.com/Frontier-Legal/casebench/commit/98b980e98cde4199cfb55402115c7604814d9737))
* **setup:** a coding agent sets Casebench up from one prompt ([#53](https://github.com/Frontier-Legal/casebench/issues/53)) ([9b9a2b5](https://github.com/Frontier-Legal/casebench/commit/9b9a2b5333f66a6ff7f1489686c6b0fd6e6c7ef0))
* **setup:** add casebench init and casebench check ([#20](https://github.com/Frontier-Legal/casebench/issues/20)) ([42fc2ee](https://github.com/Frontier-Legal/casebench/commit/42fc2eec1ab56ccef32a392f47b901f14f23ec23))
* **setup:** find the agent's providers, models and entry points in its code during init ([98cdf86](https://github.com/Frontier-Legal/casebench/commit/98cdf86f16fca5f9d25c19d2df4a8acc59b621d6))
* **setup:** guided onboarding that detects first and finds keys in .env files ([#51](https://github.com/Frontier-Legal/casebench/issues/51)) ([e6d7cf6](https://github.com/Frontier-Legal/casebench/commit/e6d7cf606e77866cde1bdc242937765ff68df876))
* **setup:** pick the judge and extraction models from a model catalog ([#23](https://github.com/Frontier-Legal/casebench/issues/23)) ([3348644](https://github.com/Frontier-Legal/casebench/commit/3348644d0f0e004c5f9cad35dcd19c7424d1c4af))
* **setup:** setup spends one search and one document, and ends with a demo ([#54](https://github.com/Frontier-Legal/casebench/issues/54)) ([2b4eb08](https://github.com/Frontier-Legal/casebench/commit/2b4eb081d319451641c441576148b2e879ebacda))
* **setup:** upgrade an existing setup in place ([#50](https://github.com/Frontier-Legal/casebench/issues/50)) ([27d5f72](https://github.com/Frontier-Legal/casebench/commit/27d5f72165d5b319b98e6d0703a8605348bc78ae))
* **suites:** mix corpora in one suite, connect several sources in init, and show each corpus's share ([#34](https://github.com/Frontier-Legal/casebench/issues/34)) ([3c4bf81](https://github.com/Frontier-Legal/casebench/commit/3c4bf8112c53afd300bdce4a1d3361ad7ff1830f))
* **targets:** reach an agent through a Python entry point, an HTTP endpoint or a command ([#7](https://github.com/Frontier-Legal/casebench/issues/7)) ([e69d283](https://github.com/Frontier-Legal/casebench/commit/e69d2831f3c4dd115d75610d0f98ab79bf0b9cfe))


### Bug Fixes

* **capture:** time each captured call with the monotonic clock ([98cdf86](https://github.com/Frontier-Legal/casebench/commit/98cdf86f16fca5f9d25c19d2df4a8acc59b621d6))
* find keys in &lt;name&gt;.env files and keep keys from .env files inside Casebench ([#52](https://github.com/Frontier-Legal/casebench/issues/52)) ([5baf950](https://github.com/Frontier-Legal/casebench/commit/5baf950fc6ac8008af7bc2772df80ee90508f82e))
* **formats:** a release leaves the report schema unchanged ([#57](https://github.com/Frontier-Legal/casebench/issues/57)) ([4845023](https://github.com/Frontier-Legal/casebench/commit/4845023497fb84add94f44144690bf6256c10f84))
* **setup:** ask for the corpus clearly inside init, with its API key ([#24](https://github.com/Frontier-Legal/casebench/issues/24)) ([80055d0](https://github.com/Frontier-Legal/casebench/commit/80055d04ebcfe64f62f8885b5577e7b6ad82bfbf))
* **setup:** check greets the agent once, and remove the demo ([#55](https://github.com/Frontier-Legal/casebench/issues/55)) ([24f4a66](https://github.com/Frontier-Legal/casebench/commit/24f4a6699931a2d2478fd8e3719d3e46229bfb79))


### Documentation

* add README and contributing guide ([fa4fbd6](https://github.com/Frontier-Legal/casebench/commit/fa4fbd6202e921881957273fc7a81d24aca959e1))
* add the contributor contract ([1f7f318](https://github.com/Frontier-Legal/casebench/commit/1f7f318bcf8ee3d7910185c932639a4c102d8b4f))
* **decisions:** propose comparable score sets, a strict pass rate and a second judge ([#28](https://github.com/Frontier-Legal/casebench/issues/28)) ([b96f265](https://github.com/Frontier-Legal/casebench/commit/b96f265249af1e12f51fd4c0e6a7a3df8018835c))
* **decisions:** propose data provider profiles for onboarding ([#25](https://github.com/Frontier-Legal/casebench/issues/25)) ([0fe1482](https://github.com/Frontier-Legal/casebench/commit/0fe1482f7ff29a2a239049b037a695803af085af))
* **decisions:** propose several corpora in one setup, routed by jurisdiction ([#31](https://github.com/Frontier-Legal/casebench/issues/31)) ([533d5c2](https://github.com/Frontier-Legal/casebench/commit/533d5c20a0a0ae4552db287d0224f596facd4d19))
* **decisions:** propose versioned formats generated from the models ([#26](https://github.com/Frontier-Legal/casebench/issues/26)) ([2fd7da9](https://github.com/Frontier-Legal/casebench/commit/2fd7da9b22badc74043ed04a18e29af692e3320d))
* **decisions:** publish each format version as its own schema file ([#27](https://github.com/Frontier-Legal/casebench/issues/27)) ([eb8cf58](https://github.com/Frontier-Legal/casebench/commit/eb8cf58ee0ed6d7189d9a775525a7a24b6cc9b04))
* **decisions:** record how statute and precedent answers are scored ([#19](https://github.com/Frontier-Legal/casebench/issues/19)) ([45f8a50](https://github.com/Frontier-Legal/casebench/commit/45f8a50ffdb69ec1a7839038f4b2807b8f2ec15c))
* drop the user-story files from the design folder ([23a9981](https://github.com/Frontier-Legal/casebench/commit/23a9981ea1e879e1c574768ade869bba66fc9429))
* name the plugin kinds in the contributor contract ([94f57f7](https://github.com/Frontier-Legal/casebench/commit/94f57f7fc095384ae62d610d23e46b8d33c3e754))
* publish the design documents and the first decision records ([eb71869](https://github.com/Frontier-Legal/casebench/commit/eb71869dd27b889be049361843bd90ff4ccf440a))
* replace the line limit with one job per file ([#6](https://github.com/Frontier-Legal/casebench/issues/6)) ([ee4791d](https://github.com/Frontier-Legal/casebench/commit/ee4791de6c8904dccb30b11a343b4e2c575e4ba4))
* ship built-in jurisdictions in the core and load them on demand ([#2](https://github.com/Frontier-Legal/casebench/issues/2)) ([fa98d6a](https://github.com/Frontier-Legal/casebench/commit/fa98d6aaa3c61121c21dbb44e900b5accb97f386))
* state each design choice and its reason on Casebench's own terms ([#22](https://github.com/Frontier-Legal/casebench/issues/22)) ([c2e4bea](https://github.com/Frontier-Legal/casebench/commit/c2e4bea185c9602f2206403728e9951fcf07eab1))
* state the licence boundary and the security policy ([f04c8c6](https://github.com/Frontier-Legal/casebench/commit/f04c8c6a42bcd5634009e9cbd23481f1a45a9dcf))


### Code Refactoring

* remove jurisdiction adapters ([#13](https://github.com/Frontier-Legal/casebench/issues/13)) ([1f1474c](https://github.com/Frontier-Legal/casebench/commit/1f1474ca7ae7db0c1c411af47dad689eb695ac05))
