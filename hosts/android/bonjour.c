#include "lan_discovery.h"
#include <android/native_activity.h>
#include <arpa/inet.h>
#include <stdio.h>
static JavaVM *vm;
static jobject activity;
static jmethodID change_port;
static void peer(JNIEnv *env,jclass cls,jstring key,jstring address,jint port,jboolean present) {
    (void)cls;
    if(!key || !address) return;
    const char *k=(*env)->GetStringUTFChars(env,key,NULL);
    const char *a=(*env)->GetStringUTFChars(env,address,NULL);
    if(k && a) {
        struct in_addr ip;
        if(!present || inet_pton(AF_INET,a,&ip)==1) ra3_lan_peer(k,k,present?ip.s_addr:0,port,present);
    }
    if(a) (*env)->ReleaseStringUTFChars(env,address,a);
    if(k) (*env)->ReleaseStringUTFChars(env,key,k);
}
static void port_changed(unsigned port,int active) {
    JNIEnv *env=NULL; int attached=0;
    if((*vm)->GetEnv(vm,(void**)&env,JNI_VERSION_1_6)!=JNI_OK) {
        if((*vm)->AttachCurrentThread(vm,&env,NULL)!=JNI_OK) return;
        attached=1;
    }
    /* Java posts to its main handler and never calls back inline. */
    jstring wire=(*env)->NewStringUTF(env,RA3_LAN_WIRE);
    if(wire) { (*env)->CallVoidMethod(env,activity,change_port,(jint)port,(jboolean)active,wire); (*env)->DeleteLocalRef(env,wire); }
    if((*env)->ExceptionCheck(env)) { (*env)->ExceptionDescribe(env); (*env)->ExceptionClear(env); }
    if(attached) (*vm)->DetachCurrentThread(vm);
}
void ra3_android_bonjour_init(ANativeActivity *a) {
    vm=a->vm;
    JNIEnv *env=NULL; int attached=0;
    if((*vm)->GetEnv(vm,(void**)&env,JNI_VERSION_1_6)!=JNI_OK) {
        if((*vm)->AttachCurrentThread(vm,&env,NULL)!=JNI_OK) return;
        attached=1;
    }
    jclass cls=(*env)->GetObjectClass(env,a->clazz);
    JNINativeMethod method={"nativeBonjourPeer","(Ljava/lang/String;Ljava/lang/String;IZ)V",(void*)peer};
    int ok=cls && (*env)->RegisterNatives(env,cls,&method,1)==0;
    if(ok) change_port=(*env)->GetMethodID(env,cls,"bonjourPort","(IZLjava/lang/String;)V");
    if(ok && change_port) activity=(*env)->NewGlobalRef(env,a->clazz);
    if((*env)->ExceptionCheck(env)) { (*env)->ExceptionDescribe(env); (*env)->ExceptionClear(env); }
    if(cls) (*env)->DeleteLocalRef(env,cls);
    if(attached) (*vm)->DetachCurrentThread(vm);
    if(activity) ra3_lan_init(port_changed,1);
    else fprintf(stderr,"[bonjour] Android NSD bridge unavailable; native LAN retained\n");
}
