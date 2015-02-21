function isAtBottom(element) {
    element = $(element)
    return element.innerHeight() + element.scrollTop() >= element[0].scrollHeight
}

String.prototype.capitalize = function() {
    return this.charAt(0).toUpperCase() + this.slice(1);
}

jQuery.fn.extend({
    setStatus: function(type, text) {
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
    if (hh > 0 || dd > 0) { s += ', ' + hh + ' hour' + plural_s(hh) }
    if (s) { s += ' and ' }
    s += mm + ' minute' + plural_s(mm)

    return {'days': dd, 'hours': hh, 'minutes': mm, 'seconds': ss, 'msecs': msec, 'string': s}
}

function updateUptime() {
    var time = $('.status-uptime').data('time')
    if (!time) { return }
    var diff = timeFromMsecs(Date.now() - parseInt(time))
    $('.status-uptime').setStatus('success', diff.string)
}


function setServerState(data) {
    if (data.state == 'started') {
        $('.status-server').setStatus('success', 'Running')
        $('.server-start').prop('disabled', true)
        $('.server-stop').prop('disabled', false)
        $('.server-restart').prop('disabled', false)
    } else if (data.state == 'stopped') {
        $('.status-server').setStatus('danger', 'Stopped')
        $('.server-start').prop('disabled', false)
        $('.server-stop').prop('disabled', true)
        $('.server-restart').prop('disabled', true)
    } else {
        $('.status-server').setStatus('warning', data.state.capitalize())
        $('.server-start').prop('disabled', true)
        $('.server-stop').prop('disabled', true)
        $('.server-restart').prop('disabled', true)
    }

    $('.status-uptime').data('time', (data.start_time || 0)*1000)
    updateUptime()
}

function setServerInfo(data) {
    if (data.info && typeof data.info.players != 'undefined') {
        $('.status-player').setStatus('success', data.info.players.online + '/' + data.info.players.max)
    } else {
        $('.status-player').setStatus('warning', '?/?')
    }
}

function reconnectOnStatus(socket, data) {
    if (data.state == 'stopped') {
        setTimeout(function() {
            data.state = 'Restarting'
            setServerState(data)
        }, 10);

        setTimeout(function() {
            socket.emit('server-start', {})
        }, 1000)

        socket.removeListener('server-state', reconnectOnStatus)
    }
}

$(document).ready(function() {
    /*
    $('.console').resizable({
        handles: 's',
        stop: function(event, ui) {
            $(this).css('width', '');
        }
    });
    */

    var socket = io.connect('/main');
    console.log(socket)
    socket.on('error', function() {
        console.error('Error:', arguments)
        $('.status-webpanel').setStatus('warning', 'Errors Occured')
    });
    socket.on('message', function() { console.log('Unhandled message:', arguments) });

    socket.on('connecting',       function() { $('.status-webpanel').setStatus('warning', 'Connecting')          })
    socket.on('reconnecting',     function() { $('.status-webpanel').setStatus('warning', 'Reconnecting')        })
    socket.on('connect_failed',   function() { $('.status-webpanel').setStatus('danger',  'Connection Failed')   })
    socket.on('reconnect_failed', function() { $('.status-webpanel').setStatus('danger',  'Reconnecting Failed') })
    socket.on('disconnect',       function() { $('.status-webpanel').setStatus('danger',  'Disconnected')        })

    socket.on('welcome', function(data) { $('.status-webpanel').setStatus('success', 'Connected') });
    socket.on('server-state', setServerState)
    socket.on('server-info', setServerInfo)
    socket.on('console-message', function(data) {
        var color = data.type == 'stderr' ? 'red' : ''

        var atBottom = isAtBottom('.console');
        $('.console').append($('<pre>').text(data.message).css('color', color))
        if (atBottom) {
            $('.console').scrollTop($('.console')[0].scrollHeight)
        }
    });

    var now = Date.now() / 1000

    var cpu_chart
    var memory_chart

    setTimeout(function() {
        cpu_chart = $('#cpu-graph').epoch({
            type: 'time.line',
            data: genHistory(1, 1, Date.now() / 1000),
            axes: ['left', 'bottom', 'right'],
            windowSize: 100,
            queueSize: 100,
            ticks: { time: 15, left: 5, right: 10}
        })
        memory_chart = $('#memory-graph').epoch({
            type: 'time.line',
            data: genHistory(1, 1, Date.now() / 1000),
            axes: ['left', 'bottom', 'right'],
            windowSize: 100,
            queueSize: 100,
            ticks: { time: 15, left: 5, right: 10}
        })
    }, 1000);

    socket.on('process-info', function(data) {
        if (!memory_chart || !cpu_chart) return;
        var now = Date.now() / 1000
        cpu_chart.push([{time: now, y: data.cpu}])
        memory_chart.push([{time: now, y: data.memory / 1024 / 1024}])
    })

    $('.server-start').click(function() { socket.emit('server-start', {}) })
    $('.server-stop').click(function() { socket.emit('server-stop', {}) })
    $('.server-restart').click(function() {
        socket.emit('server-stop', {})
        socket.on('server-state', function(data) { reconnectOnStatus(socket, data); })
    })

    $('nav li').click(function() {
        if ($(this).hasClass('active')) {
            return
        }

        var id = $(this).find('a').attr('href')
        $('nav li').removeClass('active')
        $(this).addClass('active')
        $('main > section').removeClass('active')
        $(id).addClass('active')
    })

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
    }, 15000)

    setInterval(updateUptime, 30000)
})