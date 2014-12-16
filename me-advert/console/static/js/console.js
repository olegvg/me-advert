var clockTileUpdateInterval = 1000;
var dataRefreshInterval = 300*1000;
var delayBeforePageReload = 2000;


$(function currentTime(){
    var $el = $(".current-time .icon-calendar").parent(),
    currentDate = new Date(),
    monthNames = [ "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
    "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь" ],
    dayNames = ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"];

    $el.find(".details .big").html(monthNames[currentDate.getMonth()] + " " + currentDate.getDate() + ", " + currentDate.getFullYear());
    $el.find(".details span").last().html(dayNames[currentDate.getDay()] + ", " + currentDate.getHours()+":"+ ("0" + currentDate.getMinutes()).slice(-2));
    setTimeout(function(){
        currentTime();
    }, clockTileUpdateInterval);
});

jQuery.extend( jQuery.fn.dataTableExt.oSort, {
    "date-spec-pre": function ( european_date ) {
        // For dates as "dd/mm/YYYY hh:ii:ss"

        // First trim the date
        trimed_date = european_date.replace(/^\s+/g, '').replace(/\s+$/g, '');

        // Then transform it to an integer
        if (trimed_date != '') {
            var frDatea = trimed_date.split(' ');
            var frDatea2 = frDatea[0].split('.');
            if (frDatea[1]) {
                var frTimea = frDatea[1].split(':');
                return (frDatea2[2] + frDatea2[1] + frDatea2[0] + frTimea[0] + frTimea[1]) * 1;
            } else {
                return (frDatea2[2] + frDatea2[1] + frDatea2[0]) * 1;
            }
        }else return 10000000000000;    // = l'an 1000 ...
    },

    "date-spec-asc": function(x, y) {
        return ((x < y) ? -1 : ((x > y) ? 1 : 0));
    },

    "date-spec-desc": function(x, y) {
        return ((x < y) ? 1 : ((x > y) ? -1 : 0));
    }
} );


TableTools.BUTTONS.gotoURL = $.extend( {}, TableTools.buttonBase, {
		"sButtonClass": "DTTT_button_text",
		"sButtonText": "Go to URL",
        "fnClick": function( nButton, oConfig ) {
            location.href = oConfig.sGoToURL;
        }
	} );


$.fn.dataTableExt.oApi.fnReloadAjax = function (oSettings, sNewSource, fnCallback, bStandingRedraw) {
    if (typeof sNewSource != 'undefined' && sNewSource != null) {
        oSettings.sAjaxSource = sNewSource;
    }
    this.oApi._fnProcessingDisplay(oSettings, true);
    var that = this;
    var iStart = oSettings._iDisplayStart;
    var aData = [];

    this.oApi._fnServerParams(oSettings, aData);

    oSettings.fnServerData(oSettings.sAjaxSource, aData, function (json) {
        /* Clear the old information from the table */
        that.oApi._fnClearTable(oSettings);

        /* Got the data - add it to the table */
        var aData = (oSettings.sAjaxDataProp !== "") ?
            that.oApi._fnGetObjectDataFn(oSettings.sAjaxDataProp)(json) : json;

        for (var i = 0; i < aData.length; i++) {
            that.oApi._fnAddData(oSettings, aData[i]);
        }

        oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
        that.fnDraw();

        if (typeof bStandingRedraw != 'undefined' && bStandingRedraw === true) {
            oSettings._iDisplayStart = iStart;
            that.fnDraw(false);
        }

        that.oApi._fnProcessingDisplay(oSettings, false);

        /* Callback user function - for event handlers etc */
        if (typeof fnCallback == 'function' && fnCallback != null) {
            fnCallback(oSettings);
        }
    }, oSettings);
}


function plotSummaryGraph(plot_selector, source_url){
    var url = source_url;
    var timer;

    this.changeUrl = function(newURL){
        clearTimeout(timer);
        url = newURL;
        this.begin_update()
    }

    this.begin_update = function begin_update(){
        function onDataRecieved(req) {
            var impressions = req['impr'],
                clicks = req['clck'];

            $('span#total-imprs').text(req['total-imprs']);
            $('span#total-clcks').text(req['total-clcks']);
            $('span#total-ctr').text(req['total-ctr']);
            $('span#total-reach').text(req['total-reach']);

            for (var i=0; i<impressions.length; i++){
                impressions[i][0] = impressions[i][0]*1000;
            }

            for (var c=0; c<clicks.length; c++){
                clicks[c][0] = clicks[c][0]*1000;
            }

            var data = [
                {
                    data: impressions,
                    label: "Показы",
                    xaxis: {
                        monthNames: ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
                    }
                },
                { data: clicks, label: "Клики", yaxis: 2 }
            ];

            var options = {
                xaxes: [ {
                    mode: "time",
                    monthNames: ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
                    dayNames: ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
                } ],
                yaxes: [ { min: 0 }, { position: 'right' } ],
                yaxis: {
                    minTickSize: 1,
                    tickDecimals: 0,
                    tickFormatter: function(val, axis) { return val.toFixed(axis.tickDecimals) }
                },
                legend: { position: "sw" },
                series: {
                    bars: {
                        lineWidth: 0.5,
                        show: true,
                        barWidth: req['bar-width']*1000,
                        align: "center",
                        fill: 0.6 }
                },
                colors: ['rgba(54, 142, 224, 0.7)', 'rgba(230, 58, 58, 0.7)']
            };

            $.plot(plot_selector, data, options);
        }

        $.ajax({
            url: url,
            type: "GET",
            dataType: "json",
            success: onDataRecieved
        });

        timer = setTimeout(function(){
            begin_update();
        }, dataRefreshInterval);
    };
}

function copyCode(id) {
    $(id).focus();
    $(id).select();
}