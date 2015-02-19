$(document).ready(function() {
    $('.console').resizable({
        handles: 's',
        stop: function(event, ui) {
            $(this).css("width", '');
        }
    });

    var socket = io.connect('http://' + document.domain + ':' + location.port);
    socket.on('console-message', function() {
        console.log('yolo')
        socket.emit('my event', {data: 'I\'m connected!'});
    });
})