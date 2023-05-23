import React, { useState,useEffect } from 'react';
import { StyleSheet, Text, View , Alert, FlatList} from 'react-native';
import {WebView} from 'react-native-webview';

export default function MyWebView({videoURL}){
    return (
        <View style = {styles.container}>
            <WebView
                source={{ uri: videoURL }}
            />    
        </View>
    );
}

const styles = StyleSheet.create({
    container:{
        flex:1,
        height:300,
        width:400,
    }
})