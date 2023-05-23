import React, { useState } from 'react';
import { StyleSheet, Text, View ,Button, Alert, TextInput} from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import AsyncStorage from '@react-native-async-storage/async-storage';
import NewHomePage from "./screen/NewHomePage"
import Profiles from './screen/Profiles';
import Live from './screen/Live'
import Weather from './screen/Weather';
import Settings from './screen/Settings'
import Help from './screen/Help'
import Info from './screen/Info'

const Stack = createNativeStackNavigator();

export default function App(){
    return (
        //导航堆栈
        <NavigationContainer>
            <Stack.Navigator initialRouteName="NewHomePage">
                <Stack.Screen name = "NewHomePage" component = {NewHomePage} options={{headerShadowVisible:true,headerStyle:{backgroundColor:"skyblue"},headerShown:false,title:"MyApp"}} />

                <Stack.Screen name = "Profiles" component = {Profiles} options={{animation:'slide_from_right',headerStyle:{backgroundColor:"#fafafa"}}}/>
                <Stack.Screen name = "Live" component = {Live} options={{animation:'slide_from_right'}} />
                <Stack.Screen name = "Weather" component = {Weather} options={{animation:'slide_from_right'}} />

                <Stack.Screen name = "Settings" component = {Settings} options={{animation:'slide_from_right'}} />
                <Stack.Screen name = "Help" component = {Help} options={{animation:'slide_from_right'}} />
                <Stack.Screen name = "Info" component = {Info} />
            </Stack.Navigator>
        </NavigationContainer>
    );
}
