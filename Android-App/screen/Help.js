import React, { useState } from 'react';
import { StyleSheet, Text, View , Alert, TouchableHighlight, Linking} from 'react-native';

export default function Help(){
    open = (url) => {
        Linking.openURL(url);
    }
    
    let giteeURL = "https://github.com/xiaoyuan-c/RaspberryHomework";

    return (
        <View style = {styles.container}>
            {/* <Text style = {styles.mainText}>Help</Text> */}
            <View style = {{flex:1}}>
                <View style = {{height:50,width:350,marginTop:10,justifyContent:'center'}}><Text style = {{fontSize:20,color:'blue'}}>Source Code</Text></View>
                <View style = {{height:50,width:350,marginTop:10}}>
                    <TouchableHighlight onPress={() => {this.open(giteeURL)}} activeOpacity={0.6} underlayColor="#DDDDDD" >
                        <View>
                            <View></View>
                            <View><Text style = {styles.mainText}>{giteeURL}</Text></View>
                        </View>
                    </TouchableHighlight>
                </View>
                <View style = {{height:50,width:350,marginTop:10,justifyContent:'center'}}><Text style = {{fontSize:20,color:'blue'}}>Feedback</Text></View>
                <View style = {{height:50,width:350,marginTop:10}}>
                    <TouchableHighlight onPress={() => {this.open(giteeURL+"/issues")}} activeOpacity={0.6} underlayColor="#DDDDDD" >
                        <View>
                            <View></View>
                            <View><Text style = {styles.mainText}>{giteeURL + "/issues"}</Text></View>
                        </View>
                    </TouchableHighlight>
                </View>
            </View>
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
        fontSize:20
    }
});