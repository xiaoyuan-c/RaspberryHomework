import React, { useState,useEffect } from 'react';
import { StyleSheet, Text, View , Alert, Button, TouchableOpacity} from 'react-native';
import io from 'socket.io-client';

const WebSocketBar = ({serverURL}) => {
    const [color, setColor] = useState('pink');
    const [isConnected,setIsConnected] = useState(false);
    const [socket, setSocket] = useState(null);
    const [status,setStatus] = useState(false);
    
    useEffect(() => {

    },[]);

    return (
      <View style={{ height: 20, width:360, backgroundColor: color, borderRadius:16 }}>
        <TouchableOpacity style = {{flex:1}} onPress={() => {
                setColor('skyblue');
                const newSocket = io(serverURL);
                // setSocket(newSocket);
                setStatus(true);
                newSocket.on('connect',() => {
                    console.log("Connected to server");
                    setIsConnected(true)
                });

                newSocket.on('warning_message',(msg) => {
                    console.log("received my response: ", msg);
                    setColor(msg == '1' ? 'red' : 'skyblue');
                })
                setTimeout(() => {
                    newSocket.disconnect();
                    console.log('disconnect');
                    setColor('pink');
                }, 60000);
        }}>
            <View style = {{flex:1}}></View>
        </TouchableOpacity>
      </View>
    );
};

export default WebSocketBar;