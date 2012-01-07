/*
 * jquery.jtedit.js
 *
 * a tool for displaying JSON objects as a table
 * and allowing edit of them
 *
 * open source license - cc-by
 * 
 * created by Mark MacGillivray - mark@cottagelabs.com
 *
*/


(function($){
    $.fn.jtedit = function(options) {

        // specify the defaults
        var defaults = {
            "edit":true,                    // whether or not to make the table editable
            "source":undefined,             // a source from which to GET the JSON data object
            "target":undefined,             // a target to which updated JSON should be POSTed
            "noedit":[],                    // a list of keys that should not be editable, when edit is enabled
            "hide":[],                      // a list of keys that should be hidden from view
            "data":undefined,               // a JSON object to render for editing
            "tags": [
                "type",
                "assembly",
                "name",
                "drawing",
                "assembled_by",
                "assembled_date",
                "inspected_by",
                "inspected_date",
                "assembly_history",
                "location",
                "location_history",
                "test"
            ]
        };

        // add in any overrides from the call
        var options = $.extend(defaults,options);

        // add in any options from the query URL
        var geturlparams = function() {
            var vars = [], hash;
            var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
            for (var i = 0; i < hashes.length; i++) {
                    hash = hashes[i].split('=');
                    vars.push(hash[0]);
                    if (!(hash[1] == undefined)) {
                        hash[1] = unescape(hash[1]);
                        if (hash[0] == "source") {
                            hash[1] = hash[1].replace(/"/g,'');
                        } else if (hash[0] == "data") {
                            hash[1] = $.parseJSON(hash[1]);
                        }
                    }
                    vars[hash[0]] = hash[1];
            }
            return vars;
        }
        $.extend(options,geturlparams());


        // ===============================================
        // create a pretty table out of JSON
        var tablify = function(data,edit) {
            if (edit == undefined) {
                edit = true;
            }
            if (data == null) {
                data = "";
            }
            var s = "";
            if (typeof(data) == 'object') {
                s = '<table';
                if (data.constructor.toString().indexOf("Array") != -1) {
                    s += ' class="jtedit_listtable"';
                }
                s += '><tbody>';
                for (var key in data) {
                    var loopedit = edit;
                    if ($.inArray(key,options.noedit) != -1) {
                        loopedit = false;
                    }
                    s += '<tr';
                    if ($.inArray(key,options.hide) != -1) {
                        s += ' class="jtedit_hidden"';
                    }                    
                    s += '><td>';
                    if (data.constructor.toString().indexOf("Array") == -1) {
                        s += '<input type="text" class="jtedit jtedit_key" value="' + key + '" ';
                        if (!loopedit) {
                            s += 'disabled="disabled" ';
                        }
                        s += '/>'
                    }
                    s += tablify(data[key],loopedit);
                    s += '</td></tr>';
                }
                if (data.length == 0) {
                    s += '<tr><td>';
                    s += '<input type="text" class="jtedit jtedit_key" value="" />';
                    s += '</td></tr>';
                }
                s += '<tr><td><a alt="add row" title="add row" class="jtedit_addrow" href=""> <strong>+</strong></a></td></tr>'
                s += '</tbody></table>';
            } else {
                if (data.length > 30 && edit) {
                    s += '<textarea ';
                    if (!edit) {
                        s += 'disabled="disabled" ';
                    }
                    s += 'class="jtedit jtedit_field">' + data + '</textarea>';
                } else {
                    s += '<input type="text" class="jtedit jtedit_field" value="' + data + '" ';
                    if (!edit) {
                        s += 'disabled="disabled" ';
                    }
                    s += '/>';
                }
            }
            return s;
        }


        // ===============================================
        // parse a pretty table into JSON
        var parsetable = function(table) {
            if (table == undefined) {
                var table = $('table');
            }
            if (table.children('tbody').first().children('tr').first().children('td').children('.jtedit_key').length) {
                var json = {};
            } else {
                var json = [];
            }
            table.children('tbody').first().children('tr').each(function() {
                var val = "";
                if ($(this).children('td').children('table').length) {
                    val = parsetable($(this).children('td').children('table'));
                } else {
                    val = $(this).children('td').children('.jtedit_field').val();
                }
                if ($(this).children('td').children('.jtedit_key').length) {
                    if ($(this).children('td').children('.jtedit_key').val().length != 0) {
                        json[$(this).children('td').children('.jtedit_key').val()] = val;
                    }
                } else {
                    if (val != undefined) {
                        if (val.length > 0 || typeof(val) == 'object') {
                            json.push(val);
                        }
                    }
                }
            });
            return json;
        }
        
        // make everything in the JSON texbox selected by default
        var selectall = function(event) {
            $(this).select();
        }
        // prevent unselect on chrome mouseup
        var selectallg = function(event) {
            event.preventDefault();
            $(this).select();
        }

        var updates = function(event) {
            $('#jtedit_json').val(JSON.stringify(parsetable(),"","    "));
            $(this).removeClass('text_empty');
            if ($(this).val() == "") {
                $(this).addClass('text_empty');
            }
        }

        var jtedit_addrow = function(event) {
            event.preventDefault();
            var inputcount = $(this).parent().parent().prev().find('input').length
            var tablecount = $(this).parent().parent().prev().find('table').length
            if (inputcount == 2 || inputcount + tablecount == 2) {
                $(this).before('<tr><td><input type="text" class="jtedit jtedit_key text_empty" /><input type="text" class="jtedit jtedit_field text_empty" /></td></tr>');
            } else {
                $(this).before('<tr><td><input type="text" class="jtedit jtedit_field text_empty" /></td></tr>');
            }
            $(this).prev().find('input').autoResize({"minWidth": 150,"maxWidth": 500,"minHeight": 20,"maxHeight": 200,"extraSpace": 10});
            $(this).prev().find('input').bind('blur',updates).bind('mouseup',selectallg);
            $(this).prev().find('.jtedit_key').autocomplete({source:options.tags});
        }


        // ===============================================
        // get data from a source URL
        was_in_assembly = ""
        was_in_location = ""
        var data_from_source = function(sourceurl) {
            $.ajax({
                url: sourceurl
                , type: 'GET'
                , success: function(data, statusText, xhr) {
                    if (!(data.responseText == undefined)) {
                        data = data.responseText;
                        data = data.replace(/[\r|\n]+/g,'');
                        data = data.replace(/^.*?(?={)/,'').replace(/[^}]+$/,'');
                        data = data.replace('</p>','').replace('</p>','');
                        data = $.parseJSON(data);
                    }
                    options.data = data;
                    $('#jtedit').prepend(tablify(options.data,options.edit));
                    jtedit_bindings();
                    $('#jtedit_json').val(JSON.stringify(parsetable(),"","    "));
                    // an addition to track assemnbly and location updates
                    if (options.data.in_assembly) {
                        was_in_assembly = options.data.in_assembly
                    }
                    if (options.data.location) {
                        was_in_location = options.data.location
                    }
                }
                , error: function(xhr, message, error) {
                    alert("Sorry. Your data could not be parsed from " + sourceurl + ". Please try again, or paste your data into the provided field.");
                    console.error("Error while loading data from ElasticSearch", message);
                    throw(error);
                }
            });
        }

        // ===============================================
        // setup up the jtedit screen
        var jtedit_setup = function(obj) {
            // append the jtedit div, put the editor, the menus and the raw JSON in it
            $('#jtedit',obj).remove();
            $(obj).append('<div id="jtedit" class="clearfix"></div>');
            $('#jtedit').append('<textarea id="jtedit_json">' + JSON.stringify(parsetable(),"","    ") + '</textarea>');
            $('#jtedit_json').hide();
        }
        
        // apply binding to jtedit parts
        var jtedit_bindings = function() {
            $('.jtedit').autoResize({"minWidth": 150,"maxWidth": 500,"minHeight": 20,"maxHeight": 200,"extraSpace": 10});
            $('.jtedit').bind('blur',updates);
            $('.jtedit_key').bind('mouseup',selectallg);
            $('.jtedit_field').bind('mouseup',selectallg);
            $('.jtedit_addrow').bind('click',jtedit_addrow);
            $('.jtedit_key').autocomplete({source:options.tags});
            $('.jtedit_field').each(function() {
                if ( $(this).prev('input').hasClass('jtedit_key') ) {
                    if ( $(this).prev('input').val().search("_date") != -1 ) {
                        $(this).datetimepicker({ dateFormat: 'yy-mm-dd' })
                    }
                }
            })
        }


        // ===============================================
        // create the plugin on the page
        return this.each(function() {

            obj = $(this);
            jtedit_setup(obj);
            
            if (!options.data) {
                if (options.source) {
                    data_from_source(options.source);
                } else {
                    data_from_user();
                }
            } else {
                $('#jtedit').prepend(tablify(options.data,options.edit));
                jtedit_bindings();
                $('#jtedit_json').val(JSON.stringify(parsetable(),"","    "));
            }

        });

    }
})(jQuery);




