import React, { useState, useEffect } from 'react';
import { StyleSheet, Text, View , Alert, Button} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { FontAwesome5 } from '@expo/vector-icons';
import { Ionicons } from '@expo/vector-icons';

const getData = async (key) => {
    try {
      let data = await AsyncStorage.getItem(key);
      return data;
    } catch(error) {
      return "null";
    }
}

export default function Weather(){
    const [serverURL, setServerURL] = useState();
    const [data,setData] = useState("");
    
    async function getServerURL(){
        try {
           let url = await AsyncStorage.getItem("ServerURL");
           setServerURL(url);
        } catch (error) {
            console.log(error);
        }
    }

    async function getWeather(){
        try {
            let response = await fetch(serverURL + "/weather",{
                method:"GET",
            });
            let data = await response.json().then((data) => {
                setData(JSON.stringify(data));
            });
        } catch (error) {
            // Alert.alert("ERROR",error.toString(),[{text:"OK",style: "default"}]);
        }
    }

    async function update(){
        try {
            let response = await fetch(serverURL + "/weather",{
                method:"GET",
            });
            let data = await response.json().then((data) => {
                setData(JSON.stringify(data));
            });
        } catch (error) {
            Alert.alert("ERROR",error.toString(),[{text:"OK",style: "default"}]);
        }
    }

    useEffect(() => {
        getServerURL();
        // console.log(serverURL)
        // getWeather();
    }, []);

    return (
        <View style = {styles.container}>
            {/* <Text style = {styles.mainText}>Weather</Text> */}
            <View style = {{backgroundColor:"#ffd700",height:80,width:360,borderRadius:10,marginTop:15,flexDirection:'row',alignItems:'center'}}>
                <View style = {{flex:1,justifyContent:'center',alignItems:'center'}}><FontAwesome5 name="temperature-high" size={30} color="black" /></View>
                <View style = {{flex:1}}><Text style = {{color:'#1C1C1C',fontSize:20}}>Temp: </Text></View>
                <View style = {{flex:2}}><Text style = {{color:'#1C1C1C',fontSize:20,marginLeft:20}}>{(data == "") ? "" :JSON.parse(data).Temp+"°C"}</Text></View>
            </View>
            <View style = {{backgroundColor:"#66ccff",height:80,width:360,borderRadius:10,marginTop:10,flexDirection:'row',alignItems:'center'}}>
                <View style = {{flex:1,justifyContent:'center',alignItems:'center'}}><Ionicons name="water" size={30} color="black" /></View>
                <View style = {{flex:1}}><Text style = {{color:'#1C1C1C',fontSize:20}}>Humidity: </Text></View>
                <View style = {{flex:2}}><Text style = {{color:'#1C1C1C',fontSize:20,marginLeft:20}}>{(data == "") ? "" :JSON.parse(data).Humidity+"%"}</Text></View>
            </View>
            <View style = {{width:360,margin:20}}><Button title = "Refresh" color="#32CD32" onPress={update}/></View>
        </View>
    );
}

const styles = StyleSheet.create({
    container:{
        flex:1,
        // justifyContent:'center',
        alignItems:'center',
        backgroundColor:"#fafafa",
    },
    mainText:{
        textAlign:'center',
        fontSize:20
    }
});