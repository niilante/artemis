from datetime import timedelta

# ========================
# MAIN SETTINGS

# make this something secret in your overriding app.cfg
SECRET_KEY = "default-key"
REMEMBER_COOKIE_DURATION = timedelta(minutes=60)
PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)

# contact info
ADMIN_NAME = "Cottage Labs"
ADMIN_EMAIL = ""

# service info
SERVICE_NAME = "Artemis"
SERVICE_TAGLINE = ""
HOST = "0.0.0.0"
DEBUG = True
PORT = 5002

# elasticsearch settings
ELASTIC_SEARCH_HOST = "http://127.0.0.1:9200" # remember the http:// or https://
ELASTIC_SEARCH_DB = "artemisv2"
INDEX_VERSION_GTONE = True # False for ES versions below 1, True for versions above 1
INITIALISE_INDEX = True # whether or not to try creating the index and required index types on startup

# list of superuser account names
SUPER_USER = ["test","admin"]

# Can people register publicly? If false, only the superuser can create new accounts
PUBLIC_REGISTER = False

# can anonymous users get raw JSON records via the query endpoint?
PUBLIC_ACCESSIBLE_JSON = True 

CURATED_FIELDS = ["supplier", "location", "test_type","manufacturer","staff"]


# ========================
# MAPPING SETTINGS
# a dict of the ES mappings. identify by name, and include name as first object name
# and identifier for how non-analyzed fields for faceting are differentiated in the mappings
FACET_FIELD = ".exact"
MAPPINGS = {
    "record" : {
        "record" : {
            "properties": {
                "created_date": {
                    "type": "date",
                    "format" : "yyyy-MM-dd mmss||date_optional_time"
                },
                "updated_date": {
                    "type": "date",
                    "format" : "yyyy-MM-dd mmss||date_optional_time"
                },
                "attachments":{
                    "properties": {
                        "attachment": {
                            "type": "attachment"
                        }
                    }
                }
            },
            "date_detection" : False,
            "dynamic_templates" : [
                {
                    "dates" : {
                        "path_match" : "date.*",
                        "mapping" : {
                            "type" : "multi_field",
                            "fields" : {
                                "{name}" : {"type" : "date"},
                                "format" : "yyyy-MM-dd mmss||date_optional_time"
                            }
                        }
                    }
                },
                {
                    "postdates" : {
                        "path_match" : ".*date",
                        "mapping" : {
                            "type" : "multi_field",
                            "fields" : {
                                "{name}" : {"type" : "date"},
                                "format" : "yyyy-MM-dd mmss||date_optional_time"
                            }
                        }
                    }
                },
                {
                    "default" : {
                        "match" : "*",
                        "match_mapping_type": "string",
                        "mapping" : {
                            "type" : "multi_field",
                            "fields" : {
                                "{name}" : {"type" : "{dynamic_type}", "index" : "analyzed", "store" : "no"},
                                "exact" : {"type" : "{dynamic_type}", "index" : "not_analyzed", "store" : "yes"}
                            }
                        }
                    }
                }
            ]
        }
    }
}
MAPPINGS['account'] = {"account": MAPPINGS["record"]["record"]}
MAPPINGS['curated'] = {"curated": MAPPINGS["record"]["record"]}
MAPPINGS['note'] = {"note": MAPPINGS["record"]["record"]}




# ========================
# QUERY SETTINGS

# list index types that should not be queryable via the query endpoint
NO_QUERY = ['account']

# list additional terms to impose on anonymous users of query endpoint
# for each index type that you wish to have some
# must be a list of objects that can be appended to an ES query.bool.must
# for example [{'term':{'visible':True}},{'term':{'accessible':True}}]
ANONYMOUS_SEARCH_TERMS = {
    "pages": [{'term':{'visible':True}},{'term':{'accessible':True}}]
}

# a default sort to apply to query endpoint searches
# for each index type that you wish to have one
# for example {'created_date' + FACET_FIELD : {"order":"desc"}}
DEFAULT_SORT = {
    "pages": {'created_date' + FACET_FIELD : {"order":"desc"}}
}


