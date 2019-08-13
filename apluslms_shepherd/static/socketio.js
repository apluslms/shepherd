
var socket = io.connect('http://' + document.domain + ':' + 5001);
    socket.on('update', function(data) {
        console.log(data)
        $("#"+data.instance_id+".table-number").html(data.build_number);
        $("#"+data.instance_id+".table-action").html(data.current_action);
        if (data.current_state !== null) {
            $("#" + data.instance_id + ".table-state").html(data.current_state);
        }
    });
        socket.on('connect', function() {
      console.log('connect')
    });
