import React, { useState,useEffect } from 'react';
import { StyleSheet, Text, View , Alert, Button} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import MyVideo from '../components/MyVideo';
import WebSocketBar from '../components/WebSocketBar';
import MyWebView from '../components/MyWebView'

const getData = async (key) => {
    try {
      let data = await AsyncStorage.getItem(key);
      return data;
    } catch(error) {
      return "null";
    }
}

export default function Live(){
    const [videoURL,setVideoURL] = useState("");
    const [serverURL,setServerURL] = useState("");
    const [isLoading,setIsLoading] = useState(true);

    useEffect(() => {
        async function getVideoURL(){
            let videoURI = await getData("VideoURL");
            setVideoURL(videoURI);
            return Promise.resolve();
        }
        async function getServerURL(){
            let serverURL = await getData("ServerURL");
            setServerURL(serverURL);
            return Promise.resolve();
        }
        // getVideoURL();
        // getServerURL();

        Promise.all([getVideoURL(), getServerURL()]).then(() => {
            setIsLoading(false);
          }).catch((error) => {
            console.log(error);
          });
    },[])

    async function turnLeft(){
        try {
            let response = await fetch(serverURL + "/left",{
                method:"POST",
            });
            let data = await response.json().then((data) => {
                // console.log(data);
            });
        } catch (error) {
            Alert.alert("ERROR",error.toString(),[{text:"OK",style: "default"}]);
        }
    }

    async function turnRight(){
        try {
            let response = await fetch(serverURL + "/right",{
                method:"POST",
            });
            let data = await response.json().then((data) => {
                // console.log(data);
            });
        } catch (error) {
            Alert.alert("ERROR",error.toString(),[{text:"OK",style: "default"}]);
        }
    }

    return (
        <View style = {styles.container}>
            <WebSocketBar serverURL = {serverURL} />
            <View style = {{flex:1,marginTop:10}}>
                {isLoading ? (<View><Text style = {{fontSize:16}}>Loading...</Text></View>) : (
                    <View style = {{flex:1}}>
                        {/* <MyVideo videoURI={videoURL} /> */}
                        <MyWebView videoURL={videoURL} />
                        <View style = {{height:60,flexDirection: 'row',marginTop:10,marginBottom:10,alignItems:'center',justifyContent:'center'}}>
                            <View style = {{flex:1,paddingRight:10}}><Button title='left' onPress={turnLeft}></Button></View>
                            <View style = {{flex:1,paddingLeft:10}}><Button title='right' onPress={turnRight}></Button></View>
                        </View>
                    </View>
                )}
            {/* <View><Text>122341111144412</Text></View> */}
            </View>
        </View>
    );
}

const styles = StyleSheet.create({
    container:{
        flex:1,
        justifyContent:'center',
        alignItems:'center',
        backgroundColor:"#fafafa",
    },
    mainText:{
        textAlign:'center',
        fontSize:20
    }
});