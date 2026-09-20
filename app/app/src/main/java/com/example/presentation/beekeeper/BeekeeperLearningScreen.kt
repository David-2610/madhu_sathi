package com.example.presentation.beekeeper

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.core.ui.HoneyButton
import com.example.core.ui.HoneyOutlinedTextField
import com.example.core.ui.StatusBadge

data class LearningGuideItem(
    val id: String,
    val title: String,
    val category: String,
    val summary: String,
    val benchmark: String,
    val steps: List<String>,
    val promptQuery: String,
    val icon: ImageVector
)

data class ChecklistTask(
    val id: String,
    val label: String,
    val detail: String,
    var isDone: Boolean = false
)

data class QuizQuestion(
    val id: Int,
    val question: String,
    val options: List<String>,
    val correctIndex: Int,
    val explanation: String
)

@Composable
fun BeekeeperLearningScreen(
    viewModel: BeekeeperViewModel
) {
    val uiState by viewModel.uiState.collectAsState()

    var activeSubTab by remember { mutableIntStateOf(0) } // 0: Guides, 1: Checklists, 2: Quiz, 3: AI Specialist
    var searchQuery by remember { mutableStateOf("") }
    var selectedCategory by remember { mutableStateOf("ALL") }
    var customAiPrompt by remember { mutableStateOf("") }

    val guides = remember {
        listOf(
            LearningGuideItem(
                id = "kvic_purity",
                title = "KVIC Grade-A Honey Certification",
                category = "QUALITY",
                summary = "Official purity, moisture, and chemical residue compliance standards by the Khadi & Village Industries Commission.",
                benchmark = "Moisture < 20% | F/G Ratio > 0.95 | HMF < 80 mg/kg | Zero Antibiotics",
                steps = listOf(
                    "Sample extraction only from combs that are at least 80% capped with wax by the bees.",
                    "Use an optical honey refractometer calibrated at 20°C to verify moisture level is below 20%.",
                    "Store exclusively in food-grade Stainless Steel 304 drums or food-grade glass jars.",
                    "Never exceed 45°C during warming/liquefying; excessive heat spikes HMF levels and destroys natural invertase enzymes.",
                    "Ensure coarse filtration without ultra-fine pressure filtering to preserve natural flower pollen fingerprints."
                ),
                promptQuery = "How can I prevent high honey moisture and ensure KVIC Grade-A certification?",
                icon = Icons.Default.Verified
            ),
            LearningGuideItem(
                id = "hive_thermo",
                title = "Colony Brood Nest & Thermal Management",
                category = "HEALTH",
                summary = "Maintaining the critical 34.5°C–35.5°C central incubation temperature for healthy worker bee development.",
                benchmark = "Optimal 34.5°C–35.5°C | Warning < 32°C or > 38°C",
                steps = listOf(
                    "Monitor internal IoT temperature readings daily for abnormal thermal dips.",
                    "Winter / Monsoon: Reduce hive entrance width and install top insulation quilt to preserve cluster warmth.",
                    "Summer: Position apiary under shaded groves and maintain clean running water sources within 50 meters.",
                    "Brood chilling occurs rapidly when temperatures drop below 32°C during cold snaps; unite weak colonies before winter."
                ),
                promptQuery = "What steps should I take if my hive temperature drops below 32 degrees Celsius?",
                icon = Icons.Default.DeviceThermostat
            ),
            LearningGuideItem(
                id = "swarm_acoustics",
                title = "Acoustic Swarm Detection & Prevention",
                category = "HEALTH",
                summary = "Interpreting hive acoustic humming frequency and decibel spikes before the prime swarm absconds.",
                benchmark = "Normal Hum: 45–55 dB | Swarm Piping: > 85 dB",
                steps = listOf(
                    "When hive acoustic levels rise above 85 dB, listen for high-frequency queen piping sounds.",
                    "Immediately open brood box and inspect lower comb margins for charged queen swarm cups.",
                    "Provide extra honey super boxes to relieve colony congestion and lack of storage space.",
                    "Perform an artificial swarm split if queen cells are already sealed to prevent colony loss."
                ),
                promptQuery = "My IoT hive sound level is over 85dB. How do I prevent colony swarming?",
                icon = Icons.Default.GraphicEq
            ),
            LearningGuideItem(
                id = "varroa_pest",
                title = "Integrated Organic Pest & Mite Control",
                category = "PEST",
                summary = "Non-chemical mitigation of Varroa destructor, wax moth, and Asian hornet predators.",
                benchmark = "Threshold: > 10 natural mite drops / 24 hrs on sticky bottom board",
                steps = listOf(
                    "Install screened bottom boards with sticky paper to count natural 24-hour mite drop rates.",
                    "Apply organic Oxalic Acid sublimation or Thymol gel pads during post-harvest non-forage periods.",
                    "Never administer chemical treatments during honey flow when supers are on the hive.",
                    "Freeze stored honey combs at -12°C for 24 hours to eradicate wax moth larvae and eggs before storage.",
                    "Fit entrance hornet guards with 8mm wire mesh during autumn predator seasons."
                ),
                promptQuery = "What is the best organic treatment for Varroa mites without contaminating honey?",
                icon = Icons.Default.BugReport
            ),
            LearningGuideItem(
                id = "seasonal_calendar",
                title = "Seasonal Apiary Operations Calendar",
                category = "SEASONAL",
                summary = "Month-by-month guide aligned with Indian agro-climatic floral flow cycles.",
                benchmark = "Spring Flow (Feb-Apr) | Monsoon Dearth (Jun-Aug) | Autumn Flow (Oct-Nov)",
                steps = listOf(
                    "Spring: Inspect brood combs, add foundation sheets, rotate old dark combs, expand supers.",
                    "Monsoon: Keep apiaries elevated on ant-trapped stands, provide 2:1 sugar syrup, watch for mold.",
                    "Autumn: Harvest capped honey, test purity, begin post-harvest varroa mite monitoring.",
                    "Winter: Consolidate frames, ensure adequate winter honey reserves (minimum 8-10 kg per box)."
                ),
                promptQuery = "What are the priority beekeeping tasks during the monsoon dearth season?",
                icon = Icons.Default.CalendarMonth
            ),
            LearningGuideItem(
                id = "traceability_passport",
                title = "Digital Passport & Batch Provenance",
                category = "TRACEABILITY",
                summary = "Creating tamper-evident honey batches with cryptographic QR verification for premium buyers.",
                benchmark = "Batch Hash Matching | Origin Apiary Link | Laboratory Lab Tag",
                steps = listOf(
                    "Record extraction timestamp and hive source codes immediately after harvest.",
                    "Generate a digital batch passport linking laboratory test moisture and floral source.",
                    "Affix secure QR codes to retail jars allowing consumers to view apiary geolocation and purity proof.",
                    "Immutable ledger verification commands 30-50% higher market premium from organic honey consumers."
                ),
                promptQuery = "How does blockchain traceability and digital QR passport benefit beekeepers?",
                icon = Icons.Default.QrCode
            )
        )
    }

    val routineChecklist = remember {
        mutableStateListOf(
            ChecklistTask("1", "Check Queen Presence", "Locate queen or verify freshly laid single eggs in bottom of worker cells.", false),
            ChecklistTask("2", "Brood Pattern Inspection", "Verify uniform, compact brood pattern without excessive shotgun pepper-pot holes.", false),
            ChecklistTask("3", "Honey & Pollen Reserves", "Ensure 2-3 frames of capped honey and pollen bread are flanking the brood nest.", false),
            ChecklistTask("4", "Swarm Cell Check", "Tilt brood box and inspect bottom edges of frames for vertical queen cups.", false),
            ChecklistTask("5", "Ventilation & Moisture Check", "Inspect crown board for condensation droplets; clear hive entrance.", false),
            ChecklistTask("6", "Ant Traps & Stand Inspection", "Refill oil or water cups on hive legs to block crawling pests.", false),
            ChecklistTask("7", "IoT Sensor Hygiene", "Gently brush propolis away from probe tips to maintain accurate telemetry.", false)
        )
    }

    val harvestChecklist = remember {
        mutableStateListOf(
            ChecklistTask("h1", "80% Capped Honeycomb", "Only harvest frames where at least 80% of cells are sealed with wax.", false),
            ChecklistTask("h2", "Refractometer Moisture Test", "Take sample from uncapped patch; confirm reading is below 20.0%.", false),
            ChecklistTask("h3", "Sanitize Stainless Extractor", "Wash 304-grade stainless extractor and uncapping tray with hot potable water.", false),
            ChecklistTask("h4", "Cold Centrifugal Extraction", "Spin frames gently at ambient temperature; do not apply heat guns or heaters.", false),
            ChecklistTask("h5", "Coarse Mesh Filtration", "Pass liquid honey through coarse stainless sieve (80 mesh) to remove wax bits.", false),
            ChecklistTask("h6", "48-Hour Settling Rest", "Allow honey to rest in settling tank so micro air bubbles and foam rise to top.", false)
        )
    }

    val quizQuestions = remember {
        listOf(
            QuizQuestion(
                id = 1,
                question = "What is the maximum permissible moisture content for KVIC Grade-A certified honey?",
                options = listOf("25.0%", "20.0%", "28.0%", "15.0%"),
                correctIndex = 1,
                explanation = "KVIC standards strictly mandate moisture below 20.0%. Above 20%, natural osmophilic yeasts cause wild fermentation and spoilage."
            ),
            QuizQuestion(
                id = 2,
                question = "What is the optimal temperature range inside the brood nest of an Apis cerana / Apis mellifera colony?",
                options = listOf("26.0°C – 29.0°C", "34.5°C – 35.5°C", "39.0°C – 42.0°C", "20.0°C – 24.0°C"),
                correctIndex = 1,
                explanation = "Bees maintain brood incubation strictly between 34.5°C and 35.5°C. Temperatures under 32°C cause chilled brood and deformed pupae."
            ),
            QuizQuestion(
                id = 3,
                question = "In an IoT-monitored smart hive, what does a sudden acoustic spike above 85 dB combined with weight fluctuation usually indicate?",
                options = listOf("Incoming monsoon rainstorm", "Imminent colony swarming / Queen piping", "Wax moth infestation", "Optimal foraging activity"),
                correctIndex = 1,
                explanation = "Acoustic spikes above 85 dB with queen piping frequencies are the classic pre-swarm alert before the colony splits and departs."
            ),
            QuizQuestion(
                id = 4,
                question = "Which organic treatment method is recommended for Varroa destructor control without leaving toxic chemical residues?",
                options = listOf("Commercial synthetic organophosphates", "Oxalic acid sublimation or Thymol gel pads", "Bleach fumigation", "DDT spray around hive"),
                correctIndex = 1,
                explanation = "Organic organic acids (Oxalic acid) and plant essential oils (Thymol) naturally control mite loads without contaminating pure wax or honey."
            ),
            QuizQuestion(
                id = 5,
                question = "Why is Hydroxymethylfurfural (HMF) tested during laboratory honey authentication?",
                options = listOf("It identifies the bee species", "It detects heat damage, old age, or inverted sugar adulteration", "It counts the amount of pollen", "It measures honey sweetness"),
                correctIndex = 1,
                explanation = "HMF increases when honey is overheated (>45°C), stored in hot warehouses, or adulterated with acid-hydrolyzed sugar syrups. Fresh honey must stay under 80 mg/kg."
            )
        )
    }

    var quizUserAnswers by remember { mutableStateOf(mapOf<Int, Int>()) }
    var quizSubmitted by remember { mutableStateOf(false) }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            // Header Banner
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier.padding(14.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = "BEEKEEPER TRAINING ACADEMY",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        Text(
                            text = "KVIC Purity & Smart Apiary Learning",
                            style = MaterialTheme.typography.titleMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                    StatusBadge(status = "AI TUTOR ACTIVE")
                }
            }

            // Sub-Tab Switcher
            TabRow(
                selectedTabIndex = activeSubTab,
                modifier = Modifier.fillMaxWidth()
            ) {
                Tab(
                    selected = activeSubTab == 0,
                    onClick = { activeSubTab = 0 },
                    text = { Text("Guides") },
                    icon = { Icon(Icons.Default.MenuBook, contentDescription = null, modifier = Modifier.size(18.dp)) }
                )
                Tab(
                    selected = activeSubTab == 1,
                    onClick = { activeSubTab = 1 },
                    text = { Text("Checklists") },
                    icon = { Icon(Icons.Default.Checklist, contentDescription = null, modifier = Modifier.size(18.dp)) }
                )
                Tab(
                    selected = activeSubTab == 2,
                    onClick = { activeSubTab = 2 },
                    text = { Text("KVIC Quiz") },
                    icon = { Icon(Icons.Default.School, contentDescription = null, modifier = Modifier.size(18.dp)) }
                )
                Tab(
                    selected = activeSubTab == 3,
                    onClick = { activeSubTab = 3 },
                    text = { Text("AI Specialist") },
                    icon = { Icon(Icons.Default.Psychology, contentDescription = null, modifier = Modifier.size(18.dp)) }
                )
            }

            // Body content according to selected Sub-Tab
            when (activeSubTab) {
                // -------------------------------------------------------------
                // TAB 0: GUIDES & MANUALS
                // -------------------------------------------------------------
                0 -> {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        // Search and Category Filters
                        HoneyOutlinedTextField(
                            value = searchQuery,
                            onValueChange = { searchQuery = it },
                            label = "Search Best Practice Guides",
                            placeholder = "e.g. Varroa, Moisture, Swarming, KVIC...",
                            leadingIcon = Icons.Default.Search
                        )

                        LazyRow(
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            val categories = listOf("ALL", "QUALITY", "HEALTH", "PEST", "SEASONAL", "TRACEABILITY")
                            items(categories) { cat ->
                                FilterChip(
                                    selected = selectedCategory == cat,
                                    onClick = { selectedCategory = cat },
                                    label = { Text(cat) }
                                )
                            }
                        }

                        val filteredGuides = guides.filter { guide ->
                            (selectedCategory == "ALL" || guide.category == selectedCategory) &&
                                    (searchQuery.isBlank() ||
                                            guide.title.contains(searchQuery, ignoreCase = true) ||
                                            guide.summary.contains(searchQuery, ignoreCase = true) ||
                                            guide.benchmark.contains(searchQuery, ignoreCase = true))
                        }

                        LazyColumn(
                            verticalArrangement = Arrangement.spacedBy(12.dp),
                            modifier = Modifier.fillMaxSize(),
                            contentPadding = PaddingValues(bottom = 80.dp)
                        ) {
                            items(filteredGuides, key = { it.id }) { guide ->
                                GuideCard(
                                    guide = guide,
                                    onAskAi = {
                                        customAiPrompt = guide.promptQuery
                                        activeSubTab = 3
                                        viewModel.askAssistant(guide.promptQuery)
                                    }
                                )
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // TAB 1: FIELD CHECKLISTS
                // -------------------------------------------------------------
                1 -> {
                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(14.dp),
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(bottom = 80.dp)
                    ) {
                        // Routine Inspection Checklist Card
                        item {
                            val doneCount = routineChecklist.count { it.isDone }
                            val totalCount = routineChecklist.size
                            val pct = if (totalCount > 0) (doneCount.toFloat() / totalCount) else 0f

                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Column {
                                            Text(
                                                text = "Routine Apiary Inspection",
                                                style = MaterialTheme.typography.titleMedium,
                                                fontWeight = FontWeight.Bold
                                            )
                                            Text(
                                                text = "Completed $doneCount of $totalCount checks (${(pct * 100).toInt()}%)",
                                                style = MaterialTheme.typography.bodySmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                        }
                                        if (doneCount == totalCount) {
                                            StatusBadge(status = "INSPECTION COMPLETE")
                                        }
                                    }

                                    LinearProgressIndicator(
                                        progress = { pct },
                                        modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp))
                                    )

                                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                        routineChecklist.forEachIndexed { index, task ->
                                            ChecklistRow(
                                                task = task,
                                                onToggle = { routineChecklist[index] = task.copy(isDone = !task.isDone) }
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        // Pre-Harvest Extraction Checklist
                        item {
                            val doneHarvest = harvestChecklist.count { it.isDone }
                            val totalHarvest = harvestChecklist.size
                            val pctH = if (totalHarvest > 0) (doneHarvest.toFloat() / totalHarvest) else 0f

                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Column {
                                            Text(
                                                text = "Pre-Harvest & Extraction Protocol",
                                                style = MaterialTheme.typography.titleMedium,
                                                fontWeight = FontWeight.Bold
                                            )
                                            Text(
                                                text = "Completed $doneHarvest of $totalHarvest standards (${(pctH * 100).toInt()}%)",
                                                style = MaterialTheme.typography.bodySmall,
                                                color = MaterialTheme.colorScheme.onSurfaceVariant
                                            )
                                        }
                                        if (doneHarvest == totalHarvest) {
                                            StatusBadge(status = "KVIC READY")
                                        }
                                    }

                                    LinearProgressIndicator(
                                        progress = { pctH },
                                        modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp))
                                    )

                                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                        harvestChecklist.forEachIndexed { index, task ->
                                            ChecklistRow(
                                                task = task,
                                                onToggle = { harvestChecklist[index] = task.copy(isDone = !task.isDone) }
                                            )
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // TAB 2: KVIC CERTIFICATION QUIZ
                // -------------------------------------------------------------
                2 -> {
                    val answeredCount = quizUserAnswers.size
                    val totalQuiz = quizQuestions.size
                    val correctCount = quizQuestions.count { quizUserAnswers[it.id] == it.correctIndex }

                    LazyColumn(
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(bottom = 80.dp)
                    ) {
                        item {
                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text(
                                        text = "KVIC Smart Apiary Knowledge Test",
                                        style = MaterialTheme.typography.titleMedium,
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        text = "Test your expertise on Indian purity standards, brood thermoregulation, and organic pest mitigation.",
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    if (quizSubmitted) {
                                        val scorePct = (correctCount * 100) / totalQuiz
                                        Row(
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .clip(RoundedCornerShape(8.dp))
                                                .background(if (scorePct >= 80) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.errorContainer)
                                                .padding(12.dp),
                                            horizontalArrangement = Arrangement.SpaceBetween,
                                            verticalAlignment = Alignment.CenterVertically
                                        ) {
                                            Column {
                                                Text(
                                                    text = "Score: $correctCount / $totalQuiz ($scorePct%)",
                                                    style = MaterialTheme.typography.titleMedium,
                                                    fontWeight = FontWeight.Bold,
                                                    color = if (scorePct >= 80) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onErrorContainer
                                                )
                                                Text(
                                                    text = if (scorePct >= 80) "Qualified for KVIC Quality Certification!" else "Review guidelines and retest to qualify.",
                                                    style = MaterialTheme.typography.bodySmall,
                                                    color = if (scorePct >= 80) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onErrorContainer
                                                )
                                            }
                                            TextButton(onClick = {
                                                quizUserAnswers = emptyMap()
                                                quizSubmitted = false
                                            }) {
                                                Text("Retest")
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        itemsIndexed(quizQuestions) { index, q ->
                            Card(
                                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                                shape = RoundedCornerShape(12.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text(
                                        text = "Question ${index + 1} of $totalQuiz",
                                        style = MaterialTheme.typography.labelSmall,
                                        color = MaterialTheme.colorScheme.primary,
                                        fontWeight = FontWeight.Bold
                                    )
                                    Text(
                                        text = q.question,
                                        style = MaterialTheme.typography.bodyMedium,
                                        fontWeight = FontWeight.SemiBold
                                    )

                                    q.options.forEachIndexed { optIndex, optText ->
                                        val isChosen = quizUserAnswers[q.id] == optIndex
                                        val isCorrect = q.correctIndex == optIndex
                                        val bgColor = when {
                                            !quizSubmitted && isChosen -> MaterialTheme.colorScheme.primaryContainer
                                            quizSubmitted && isCorrect -> Color(0xFFD1FAE5)
                                            quizSubmitted && isChosen && !isCorrect -> Color(0xFFFEE2E2)
                                            else -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
                                        }

                                        Surface(
                                            onClick = {
                                                if (!quizSubmitted) {
                                                    quizUserAnswers = quizUserAnswers + (q.id to optIndex)
                                                }
                                            },
                                            shape = RoundedCornerShape(8.dp),
                                            color = bgColor,
                                            modifier = Modifier.fillMaxWidth()
                                        ) {
                                            Row(
                                                modifier = Modifier.padding(10.dp),
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                                            ) {
                                                RadioButton(
                                                    selected = isChosen,
                                                    onClick = {
                                                        if (!quizSubmitted) {
                                                            quizUserAnswers = quizUserAnswers + (q.id to optIndex)
                                                        }
                                                    }
                                                )
                                                Text(
                                                    text = optText,
                                                    style = MaterialTheme.typography.bodyMedium,
                                                    fontWeight = if (isChosen) FontWeight.Bold else FontWeight.Normal
                                                )
                                            }
                                        }
                                    }

                                    if (quizSubmitted) {
                                        Text(
                                            text = "Explanation: ${q.explanation}",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }
                            }
                        }

                        if (!quizSubmitted) {
                            item {
                                HoneyButton(
                                    text = "Submit & Grade Quiz ($answeredCount / $totalQuiz Answered)",
                                    onClick = { quizSubmitted = true },
                                    enabled = answeredCount > 0,
                                    icon = Icons.Default.Check
                                )
                            }
                        }
                    }
                }

                // -------------------------------------------------------------
                // TAB 3: INTEGRATED AI SPECIALIST
                // -------------------------------------------------------------
                3 -> {
                    Column(
                        modifier = Modifier.fillMaxSize(),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        // Header
                        Card(
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                            shape = RoundedCornerShape(12.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(
                                            text = "AI Apiary Specialist",
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.Bold
                                        )
                                        Text(
                                            text = if (uiState.selectedHive != null) "Diagnosing for Hive ${uiState.selectedHive!!.hiveCode}" else "General Apiary Diagnostic Mode",
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                    StatusBadge(status = "GEMINI ADVISOR")
                                }
                                
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    HoneyButton(
                                        text = "Analyze Current Telemetry",
                                        onClick = { viewModel.analyzeTelemetryWithGemini() },
                                        icon = Icons.Default.Sensors,
                                        modifier = Modifier.weight(1f)
                                    )
                                    OutlinedButton(onClick = { viewModel.clearChatHistory() }) {
                                        Icon(Icons.Default.ClearAll, contentDescription = "Clear")
                                    }
                                }
                            }
                        }

                        // Chat History
                        LazyColumn(
                            modifier = Modifier.weight(1f),
                            verticalArrangement = Arrangement.spacedBy(8.dp),
                            contentPadding = PaddingValues(bottom = 16.dp)
                        ) {
                            items(uiState.chatMessages) { msg ->
                                val isUser = msg.role == "user"
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
                                ) {
                                    Surface(
                                        shape = RoundedCornerShape(16.dp),
                                        color = if (isUser) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant,
                                        modifier = Modifier.widthIn(max = 300.dp)
                                    ) {
                                        Text(
                                            text = msg.text,
                                            modifier = Modifier.padding(12.dp),
                                            style = MaterialTheme.typography.bodyMedium,
                                            color = if (isUser) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurfaceVariant
                                        )
                                    }
                                }
                            }
                            if (uiState.isAskingAssistant) {
                                item {
                                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Start) {
                                        Surface(
                                            shape = RoundedCornerShape(16.dp),
                                            color = MaterialTheme.colorScheme.surfaceVariant,
                                        ) {
                                            Row(modifier = Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                                CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                                                Text("Gemini is analyzing...", style = MaterialTheme.typography.bodyMedium)
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Input Box
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            OutlinedTextField(
                                value = customAiPrompt,
                                onValueChange = { customAiPrompt = it },
                                placeholder = { Text("Ask Gemini a question...") },
                                modifier = Modifier.weight(1f),
                                shape = RoundedCornerShape(24.dp)
                            )
                            IconButton(
                                onClick = { 
                                    viewModel.askAssistant(customAiPrompt)
                                    customAiPrompt = ""
                                },
                                modifier = Modifier.background(MaterialTheme.colorScheme.primary, CircleShape)
                            ) {
                                Icon(Icons.Default.Send, contentDescription = "Send", tint = MaterialTheme.colorScheme.onPrimary)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun GuideCard(
    guide: LearningGuideItem,
    onAskAi: () -> Unit
) {
    var isExpanded by remember { mutableStateOf(false) }

    Card(
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(12.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.weight(1f)
                ) {
                    Icon(
                        imageVector = guide.icon,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(22.dp)
                    )
                    Text(
                        text = guide.title,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold
                    )
                }
                StatusBadge(status = guide.category)
            }

            Text(
                text = guide.summary,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )

            Surface(
                color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.5f),
                shape = RoundedCornerShape(6.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = "Standard: ${guide.benchmark}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 6.dp)
                )
            }

            AnimatedVisibility(visible = isExpanded) {
                Column(
                    verticalArrangement = Arrangement.spacedBy(6.dp),
                    modifier = Modifier.padding(top = 4.dp)
                ) {
                    Text(
                        text = "Practical Step-by-Step Protocol:",
                        style = MaterialTheme.typography.labelMedium,
                        fontWeight = FontWeight.Bold
                    )
                    guide.steps.forEachIndexed { i, step ->
                        Row(
                            verticalAlignment = Alignment.Top,
                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Text(
                                text = "${i + 1}.",
                                style = MaterialTheme.typography.bodySmall,
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary
                            )
                            Text(
                                text = step,
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                }
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(onClick = { isExpanded = !isExpanded }) {
                    Text(if (isExpanded) "Hide Details" else "Read Protocol")
                    Spacer(modifier = Modifier.width(4.dp))
                    Icon(
                        imageVector = if (isExpanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                        contentDescription = null
                    )
                }

                OutlinedButton(
                    onClick = onAskAi,
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Icon(Icons.Default.Psychology, contentDescription = null, modifier = Modifier.size(16.dp))
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("Ask AI")
                }
            }
        }
    }
}

@Composable
private fun ChecklistRow(
    task: ChecklistTask,
    onToggle: () -> Unit
) {
    Surface(
        onClick = onToggle,
        shape = RoundedCornerShape(8.dp),
        color = if (task.isDone) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.35f)
        else MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
        modifier = Modifier.fillMaxWidth()
    ) {
        Row(
            modifier = Modifier.padding(10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Checkbox(
                checked = task.isDone,
                onCheckedChange = { onToggle() }
            )
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = task.label,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = if (task.isDone) FontWeight.Bold else FontWeight.Medium
                )
                Text(
                    text = task.detail,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}
