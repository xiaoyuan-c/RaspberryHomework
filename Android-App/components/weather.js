import React, { useState,useEffect } from 'react';
import { StyleSheet, View, Button, Text, Alert } from 'react-native';

export default function Weather({serverURL}){
    const [weatherData,setWeatherData] = useState("no data available");

    async function getWeather(){
        try {
            let response = await fetch(serverURL + "/weather",{
                method:"GET",
            });
            let data = await response.json().then((data) => {
                setWeatherData(JSON.stringify(data));
            });
        } catch (error) {
            Alert.alert("ERROR",error.toString(),[{text:"OK",style: "default"}]);
        }
    }

    return (
        <View>
            <View style = {{flexDirection: 'row',justifyContent: 'space-between',alignItems: 'center'}}>
                <View style = {{marginStart:20}}>
                    <Text style = {{fontSize:20}}>WEATHER: </Text>
                </View>
                <View style = {{marginEnd:20,width:150,padding:5}}>
                    <Button title="GET WEATHER" onPress={getWeather} color="green" />
                </View>
            </View>
            <Text style = {{marginStart:15,fontSize:16}}>{weatherData}</Text>
        </View>
    );
}