function isAtBottom(element) {
    return element.innerHeight() + element.scrollTop() >= element[0].scrollHeight
}

String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

String.prototype.b64id = function() {
    return btoa(this).slice(0, this.length-2)
}

jQuery.fn.extend({
    setStatus: function(type, text) {
        if (typeof text == 'undefined') {
            text = this.children('.status').text()
        }

        this.children('.status').text(text)
        return this.removeClass(
            'label-default label-primary label-success label-info label-warning label-danger'
        ).addClass('label-'+type)
    }
})

function genHistory(entries, layers, now) {
    timestamp = now - entries

    var history = [];
    for (var k = 0; k < layers; k++) {
        history.push({ values: [] })
    }

    for (var i = 0; i < entries; i++) {
        for (var j = 0; j < layers; j++) {
            history[j].values.push({time: this.timestamp, y: 0})
        }
            timestamp++
    }

    return history
}

function get1024Base(num) {
    var r = 1;
    var i = 0;
    for (; (r*1024) < num; i++) {
        r = r * 1024;
    }

    return i;
}

function roundTo1024(num, cap, rfunc) {
    if (num <= 0 || !num) { return num; }

    var r = Math.pow(1024, Math.min(cap, get1024Base(num)))
    return rfunc(num / r) * r;
}

function myRound(to, func) {
    return function(num) {
        return func(num / to) * to
    }
}

function memoryRange(min, max) {
    if (min == 0 && max == 0) return [0, 1];
    return [
        roundTo1024(min, 2, myRound(Math.pow(10, get1024Base(min)), Math.floor)),
        roundTo1024(max, 2, myRound(Math.pow(10, get1024Base(max)), Math.ceil))
    ];
}

function memoryTicks(num) {
    function func(min, max) {
        //min = roundTo1024(min, 2, Math.floor)
        //max = roundTo1024(max, 2, Math.ceil)

        var interval = (max-min)/(num - 1)
        var ret = []
        for (i = min; i <= max; i += interval) {
            ret.push(Math.round(i))
        }

        return ret;
    }

    return func
}

function cpuRange(min, max) {
    return [0, max];
}

function timeFromMsecs(msec) {
    var hh = Math.floor(msec / 1000 / 60 / 60)
    msec -= hh * 1000 * 60 * 60
    var mm = Math.floor(msec / 1000 / 60)
    msec -= mm * 1000 * 60
    var ss = Math.floor(msec / 1000)
    msec -= ss * 1000

    var dd = Math.floor(hh / 24)
    hh -= dd * 24

    function plural_s(val) {
        return val == 1 ? '' : 's'
    }

    var s = ''
    if (dd > 0) { s += dd + ' day' + plural_s(dd) }
    if (s) { s += ', ' }
    if (hh > 0 || dd > 0) { s += hh + ' hour' + plural_s(hh) }
    if (s) { s += ' and ' }
    s += mm + ' minute' + plural_s(mm)

    return {'days': dd, 'hours': hh, 'minutes': mm, 'seconds': ss, 'msecs': msec, 'string': s}
}

function updateUptime() {
    status = 'warning'
    message = '?'

    var time = $('.status-uptime').data('time')
    if (time) {
        var diff = timeFromMsecs(Date.now() - parseInt(time))
        if (diff.seconds >= 1) {
            status = 'success'
            message = diff.string
        }
    }

    $('.status-uptime').setStatus(status, message)
}


function setServerState(data) {
    $('.status-uptime').data('time', (data.start_time || 0)*1000)
    updateUptime()

    if (data.state == 'started') {
        $('.status-server').setStatus('success', 'Running')
        $('.server-start').prop('disabled', true)
        $('.server-stop').prop('disabled', false)
        $('.server-restart').prop('disabled', false)
        $('.backup-new').prop('disabled', false)
    } else if (data.state == 'stopped') {
        $('.status-server').setStatus('danger', 'Stopped')
        $('.server-start').prop('disabled', false)
        $('.server-stop').prop('disabled', true)
        $('.server-restart').prop('disabled', true)
        $('.backup-new').prop('disabled', false)
    } else {
        $('.status-server').setStatus('warning', data.state.capitalize())
        $('.server-start').prop('disabled', true)
        $('.server-stop').prop('disabled', true)
        $('.server-restart').prop('disabled', true)
        $('.backup-new').prop('disabled', true)
    }
}

function setServerInfo(data) {
    if (data.info && typeof data.info.players != 'undefined') {
        $('.status-player').setStatus('success', data.info.players.online + '/' + data.info.players.max)
    } else {
        $('.status-player').setStatus('warning', '?/?')
    }
}


_HTML_BACKUP_BTNS = '<a class="backup-delete" href="javascript:void(0);"><i class="fa fa-times-circle"></i></a>'
_HTML_BACKUP_EMPTY = '<tr class="no-sort"><td style="color: red">No backups found</td><td></td><td></td><td></td></tr>'
_TYPES_SORT = {
    user: 0,
    monthly: 0,
    weekly: 1,
    daily: 2,
    hourly: 3
}


$(document).ready(function() {
    var tblsort_schedule = new Tablesort(document.getElementById('backup-schedule'))
    var tblsort_user = new Tablesort(document.getElementById('backup-user'))

    var cpu_chart;
    var memory_chart;
    function createCharts() {
        function _createCharts() {
            var options = {
                type: 'time.line',
                data: genHistory(1, 1, Date.now() / 1000),
                axes: ['left', 'bottom', 'right'],
                //windowSize: 10,
                windowSize: 300,
                queueSize: 1,
                historySize: 1,
                ticks: { time: 30, left: 5, right: 10 },
                tickFormats: {
                    left: Epoch.Formats.percent,
                    right: Epoch.Formats.percent,
                    top: Epoch.Formats.seconds,
                    bottom: Epoch.Formats.seconds
                },
                margins: { top: 25, right: 80, bottom: 25, left: 80 },
            }

            options.range = cpuRange
            cpu_chart = $('#cpu-graph').epoch(options)
            options.tickFormats.left = Epoch.Formats.bytes
            options.tickFormats.right = Epoch.Formats.bytes
            options.ticks.left = memoryTicks(5)
            options.ticks.right = memoryTicks(10)
            options.range = memoryRange
            memory_chart = $('#memory-graph').epoch(options)
        }

        setTimeout(_createCharts, 1000)
        $('body > nav > ul > li > a[href="#overview"]').unbind('click', createCharts)
    }
    $('body > nav > ul > li > a[href="#overview"]').click(createCharts)

    function resize() {
        $('body > nav').css('height', Math.max($(document).height(), $(window).height()) - 100 + 'px');
    }
    $(window).resize(resize);
    resize();

    var socket = io.connect('/main');

    socket.on('error', function() {
        console.error('Error:', arguments)
        $('.status-webpanel').setStatus('warning', 'Errors Occured')
    });
    socket.on('message', function() { console.log('Unhandled message:', arguments) });

    socket.on('connecting',       function() { $('.status-webpanel').setStatus('danger', 'Connecting')          })
    socket.on('reconnecting',     function() { $('.status-webpanel').setStatus('danger', 'Reconnecting')        })
    socket.on('connect_failed',   function() { $('.status-webpanel').setStatus('danger', 'Connection Failed')   })
    socket.on('reconnect_failed', function() { $('.status-webpanel').setStatus('danger', 'Reconnecting Failed') })
    socket.on('disconnect',       function() { $('.status-webpanel').setStatus('danger', 'Disconnected')        })

    socket.on('welcome', function(data) { $('.status-webpanel').setStatus('success', 'Connected') });
    socket.on('server-state', setServerState)
    socket.on('server-info', setServerInfo)
    var _ERROR_MESSAGE = '<pre style="color: red"></pre>'
    var _MESSAGE = '<pre></pre>'
    socket.on('console-message', function(data) {
        var pre = data.type == 'stderr' ?  _ERROR_MESSAGE : _MESSAGE
        var c = $('.console')

        var atBottom = isAtBottom(c);
        c.append($(pre).text(data.message))
        if (atBottom) {
            c.scrollTop($('.console')[0].scrollHeight)
        }
    });

    socket.on('server-info', function(data) {
        if (!memory_chart || !cpu_chart) return;
        var now = Date.now() / 1000
        cpu_chart.push([{time: now, y: data.cpu/100}])
        memory_chart.push([{time: now, y: data.memory}])
        //memory_chart.push([{time: now, y: 1.64 * 1024 * 1024 * 1024}])
    })

    socket.on('backup-started', function(data) {
        console.log(data)
        var text = data.type.capitalize() + ' backup in progress'
        if (data.label) {
            text += ': ' + data.label
        } else {
            text += '.'
        }

        $('<div class="alert alert-success" role="alert"></div>')
            .attr('id', data.name.b64id())
            .text(text)
            .prepend($('<i class="fa fa-cog fa-spin"></i>'))
            .appendTo('.backup-alerts')

        if ($('.status-backup').length == 0) {
            $('<label class="label status-backup label-success">Backup in progress</label>')
                .data('num', 1)
                .appendTo($('.statusbar'))
        } else {
            $('.status-backup').data().num++
        }
    })
    socket.on('backup-stopped', function(data) {
        console.log(data)
        $('#' + data.name.b64id()).remove()

        var table = data.type == 'user' ? $('#backup-user tbody') : $('#backup-schedule tbody')

        var date = $('<td></td>').text(data.datestr).attr('data-sort', data.time)
        var label = $('<td></td>').text(data.label || data.type)
        if (data.type != 'user') {
            label.attr('data-sort',  _TYPES_SORT[data.type] + '.' + (data.time | 0))
        }
        var size = $('<td></td>').text(Epoch.Formats.bytes(data.size)).attr('data-sort', data.size)
        var btn = $('<td></td>').html(_HTML_BACKUP_BTNS)
        btn.find('.backup-delete').click(backup_delete)

        var tr = $('<tr></tr>')
            .append(date)
            .append(label)
            .append(size)
            .append(btn)
            .data('name', data.name)
            .appendTo(table)

        table.find('.no-sort').remove()
        if ($('.status-backup').data('num') > 1) {
            $('.status-backup').data().num--;
        } else {
            $('.status-backup').remove()
        }

        tblsort_schedule.refresh()
        tblsort_user.refresh()
    })
    socket.on('backup-deleted', function(data) {
        $('.backup-table-outer tr').each(function() {
            if ($(this).data('name') == data.name) {
                if ($(this).parent().children('tr').length == 1) {
                    $(this).parent().append(_HTML_BACKUP_EMPTY)
                }

                $(this).remove()
            }
        })
    })

    $('.server-start').click(function() { socket.emit('server-start', {}) })
    $('.server-stop').click(function() { socket.emit('server-stop', {}) })
    $('.server-restart').click(function() {
        function handler(data) {
            if (data.state == 'stopped') {
                setTimeout(function() {
                    data.state = 'Restarting'
                    setServerState(data)
                }, 10);

                setTimeout(function() {
                    socket.emit('server-start', {})
                }, 1000)

                socket.removeListener('server-state', handler)
            }
        }

        socket.on('server-state', handler)
        socket.emit('server-stop', {})
    })

    $('.backup-new').click(function() {
        var input = $(this).parent().children('input')
        socket.emit('backup-new', {label: input.val()})
        input.val('')
    })

    function backup_delete() {
        var parent = $(this).parent().parent()
        var msg = ''
        parent.children('td:nth-child(-n+3)').each(function() { msg += '\n' + $(this).text() })
        var really = confirm('Are you sure you want to delete this backup? This cannot be undone!\n'+msg);

        if (really) {
            console.log('do it', parent.data('name'))
            socket.emit('backup-delete', {name: parent.data('name')})
        }
    }
    $('.backup-delete').click(backup_delete)

    $('body > nav > ul > li > a').click(function(event) {
        var id = $(this).attr('href')
        $('body > nav > ul > li').removeClass('active')
        $(this).parent().addClass('active')
        $('main > section').removeClass('active')
        $(id + '_inner').addClass('active')
    })

    if (location.hash) {
        $('body > nav > ul > li > a[href="' + location.hash + '"]').click()
    } else {
        $('body > nav > ul > li.active > a').click()
    }

    $(window).on('hashchange', function() {
        window.scrollTo(0, 0);
    })

    var was_at_bottom = true;
    $('body > nav > ul > li > a[href="#console"]').click(function() {
        if ($('.console').data('bottom')) {
            setTimeout(function() {$('.console').scrollTop($('.console')[0].scrollHeight)}, 10)
        }
    })
    $('.console').scroll(function() {
        $(this).data('bottom', isAtBottom('.console'))
    })
    $('.console').data('bottom', true)

    $('.command-input').keyup(function(event) {
        if (event.keyCode == 13) {  // enter
            socket.emit('command', {command: $(this).val()})
            $(this).val('')
        }
    })

    setInterval(function() {
        if (socket.socket.connected) {
            socket.emit('request-server-info', {})
        }
    }, 1000)
    setInterval(updateUptime, 30000)
    if (location.hash) {
        setTimeout(function() {
            window.scrollTo(0, 0);
    }, 1);
}
})