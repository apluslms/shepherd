var socket = io('http://127.0.0.1:5001', {
transportOptions: {
    polling: {
      extraHeaders: {
        'Origin': 'http://127.0.0.1:5001'
      }
    }
  }
});
    socket.on('update', function(data) {
        console.log(data);
        $("#"+data.instance_id+".table-number").html(data.build_number);
        $("#"+data.instance_id+".table-action").html(data.current_action);
        $("#"+data.instance_id+".table-state").html(data.current_state);
    });
        socket.on('connect', function() {
      console.log('connect')
    });