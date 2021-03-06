
import requests, json

vals = {"location":[
"",
" aip",
" ",
" AIP",
" AIP Assembly Room 1",
" AMG Electrical Assembly Area",
" AMG Mechanical Assembly Room 2",
" AMG Mechanical Inspection Room",
" Blue instrumentation cupboard",
" FK1 DDM1 Cabinet",
" FK1 DDM2 Cabinet ",
" FK1 DDP Cabinet",
" FK1 Spares Crate ",
" HT DDP Cabinet",
" LTS1",
" LTS3",
" LTS4",
" LTS5",
" NE2",
" PS1",
" TC1",
" TC2",
" TC4",
" WR1",
" WR2",
" aip",
"AIP",
"Artemis",
"Edin",
"In cast block for 1st test",
"LTS 3 Solidworks > M210 Q40 800KW Driveline",
"LTS-4",
"MHI - Shimo",
"MHI Japan",
"MHI Yokohama",
"MHI japan",
"MHI-S",
"S210 DD89 used as accumulator manifold.",
"S:\Artemis Master\Test Rigs\LTS-3 life time test container\Solidworks\M210\M210 Q40 800KW Driveline",
"Test Cell 2",
"aip",
"aip Q144 DD84",
"artemis",
"s210 dd89"
],
"manufacturer": [
"",
" AIP",
" Agilent",
" Burnett and Hillman",
" ERIKS",
" Euroscot",
" Evershed and Vignoles",
" FAG",
" Gossen Metrawatt ",
" Greco",
" Hallmark Electronics",
" Honeywell",
" Hydraumatec",
" Kern",
" Kingfield Electronics",
" LEE Spring",
" Lazer Engineering Scotland Ltd",
" Mitutoyo",
" Newbury Electronics",
" Omega Engineering Limited",
" PCB Cart",
" Pico",
" QPE (Quality Precision Electronics Limited)",
" RS Components",
" SKF",
" Sauer Danfoss",
" Springmasters",
" Swan Enviro",
" Tenma",
" Wera",
"AIP",
"Artemis",
"Artemis Workshop",
"Castle Precision Engineering",
"Castle precision",
"EAP Seals",
"GRECO",
"Hallmark",
"Hallmark Electronics LTD",
"Kingfield",
"Kingfield Electronics",
"Kingfield Electronics LTD",
"Kingfield Electronics LTD.",
"Kyowa",
"Quality Precision Electronics Ltd",
"Quality Precision Engineering",
"RS",
"STL",
"TEC",
"WEC",
"abbey",
"aip",
"artemis",
"castle",
"cpe ",
"economos",
"euroscot",
"greco",
"lee spring",
"magnet schultz",
"magnet schulz",
"mhi",
"pentland",
"skf",
"technifast"
],
"supplier":[
"",
" AIP",
" Burnett and Hillman",
" EAP Seals",
" ERIKS",
" Farnell Element 14",
" Hallmark Electronics",
" Kingfield Electronics",
" Lazer Engineering Scotland Ltd",
" Mouser",
" Newbury Electronics",
" Omega Engineering Limited",
" PCB Cart",
" QPE (Quality Precision Electronics Limited)",
" RS Components",
" SKF",
" aip",
" technifast",
"AIP",
"Castle",
"Castle Precision",
"Castle precision",
"E V engineering",
"ERIKS",
"EV",
"FAG",
"INA via SD",
"Kingfield Electronics",
"LEE SPRING",
"LEE spring",
"Lee spring",
"MSM",
"Magnet Schultz Memmingen",
"Magnet-Schultz",
"SKF",
"aip",
"burnett and hillman",
"burnett/hillman",
"euroscot",
"greco",
"hispec",
"hydraumatec",
"lee spring",
"sauer danfoss",
"skf",
"springmasters",
"technifast"
],
"test_type": [
"",
" AIP1106c - XPHS2 FET Board_01B Test Procedure",
" AIP1219a - FET Module Indicator Board Test Procedure",
" AIP1232a - FET Module Test Procedure",
" AIP1232b - FET Module Test Procedure",
" AIP1393 - FPGA3 7MW FET Module Conformal Coating Procedure",
" AIP1393 - FPGA3 7MW FET Module Conformal Coating Process",
" AIP1395 - XPHS2 7MW FET Module Conformal Coating Procedure",
" AIP1395 - XPHS2 7MW FET Module Conformal Coating Procedure - partial (repair following modification)",
" AIP1407 - FET Module 1.0 Display Boards Conformal Coating Procedure",
" AIP1408 - FET module indicator board_01A Conformal Coating Procedure",
" AIP1412 - P.C.B. electrical assembly engraving procedure",
" AIP1413 - A.M.C. DC Power Board_01E conformal coating procedure",
" AIP1414 - A.M.C. ST10 Processor Board II_01A conformal coating procedure",
" AIP1416 - A.M.C. Communications Board_01C conformal coating procedure",
" AIP1417 - A.M.C. Analogue Conn Board 2_01A board conformal coating procedure",
" AIP1418 - A.M.C. Digital Connector Board 2_01A conformal coating procedure",
" AIP1419 - A.M.C. Communications Board_01C CAN1 removal procedure",
" AIP1450a - HS16 FET Board_01A Test Procedure",
" Procedure description document attached",
"Simple visual inspection",
"no_curated_values_available"
],
"user":[
"",
" not inspected",
"AIP/MHI",
"Alex",
"Chris ",
"GH",
"Gordon H",
"M Green",
"MHI",
"NM",
"Pierre",
"gh",
"gordon",
"johnS",
"not inspected",
"peter"
]
}



for k in vals.keys():
    for val in vals[k]:
        rec = {"type":k,"value":val,"id":k+'_'+val.replace(' ','')}
        requests.post('http://localhost:9200/artemisv2/curated/' + rec["id"], data=json.dumps(rec))