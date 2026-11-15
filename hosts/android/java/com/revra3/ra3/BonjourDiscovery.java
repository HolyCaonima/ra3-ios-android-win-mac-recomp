package com.revra3.ra3;

import android.content.Context;
import android.net.nsd.NsdManager;
import android.net.nsd.NsdServiceInfo;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import java.net.Inet4Address;
import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.HashMap;
import java.util.Map;
import java.util.UUID;

/** Optional DNS-SD provider. All state is confined to the main handler. */
final class BonjourDiscovery {
    private static final String TYPE="_liftingra3._udp.";
    private final Handler handler=new Handler(Looper.getMainLooper());
    private final NsdManager nsd;
    private final String prefix="LRA3-"+UUID.randomUUID().toString();
    private String wire;
    private final Map<Integer,NsdManager.RegistrationListener> registrations=new HashMap<>();
    private final Map<String,NsdServiceInfo> found=new HashMap<>();
    private final Map<String,String> addresses=new HashMap<>();
    private final ArrayDeque<NsdServiceInfo> pending=new ArrayDeque<>();
    private NsdManager.DiscoveryListener browser;
    private boolean resolving;
    private int generation;
    BonjourDiscovery(Context context) { nsd=(NsdManager)context.getSystemService(Context.NSD_SERVICE); }
    void port(int port,boolean active,String protocol) { handler.post(()->change(port,active,protocol)); }
    private void failure(String operation,int code) { Log.w("ra3","[bonjour] "+operation+": "+code); }
    private void remove(String name) {
        found.remove(name);
        String address=addresses.remove(name);
        if(address!=null) GameActivity.nativeBonjourPeer("android:"+name,address,0,false);
    }
    private void stopBrowse() {
        generation++;
        NsdManager.DiscoveryListener old=browser; browser=null;
        if(old!=null) try { nsd.stopServiceDiscovery(old); } catch(IllegalArgumentException e) { Log.w("ra3","[bonjour] stop",e); }
        for(String name:new java.util.ArrayList<>(addresses.keySet())) remove(name);
        found.clear(); pending.clear();
        // An old resolve remains in flight. Serialize the next one until its callback.
    }
    private void change(final int port,boolean active,String protocol) {
        if(nsd==null || port<8086 || port>8093) return;
        wire=protocol;
        if(!active) {
            NsdManager.RegistrationListener old=registrations.remove(port);
            if(old!=null) try { nsd.unregisterService(old); } catch(IllegalArgumentException e) { Log.w("ra3","[bonjour] unregister",e); }
            if(registrations.isEmpty()) stopBrowse();
            return;
        }
        if(browser==null) startBrowse();
        if(registrations.containsKey(port)) return;
        NsdServiceInfo info=new NsdServiceInfo();
        info.setServiceName(prefix+"-"+port); info.setServiceType(TYPE); info.setPort(port); info.setAttribute("wire",wire);
        NsdManager.RegistrationListener listener=new NsdManager.RegistrationListener() {
            public void onServiceRegistered(NsdServiceInfo service) {
                handler.post(()->{
                    if(registrations.get(port)!=this) try { nsd.unregisterService(this); } catch(IllegalArgumentException ignored) { }
                    else Log.i("ra3","[bonjour] registered "+service.getServiceName());
                });
            }
            public void onRegistrationFailed(NsdServiceInfo service,int error) {
                handler.post(()->{ if(registrations.get(port)==this) registrations.remove(port); failure("register",error); });
            }
            public void onServiceUnregistered(NsdServiceInfo service) { }
            public void onUnregistrationFailed(NsdServiceInfo service,int error) { failure("unregister",error); }
        };
        registrations.put(port,listener);
        try { nsd.registerService(info,NsdManager.PROTOCOL_DNS_SD,listener); }
        catch(RuntimeException e) { registrations.remove(port); Log.w("ra3","[bonjour] register",e); }
    }
    private void startBrowse() {
        final int epoch=++generation;
        browser=new NsdManager.DiscoveryListener() {
            public void onDiscoveryStarted(String type) { }
            public void onDiscoveryStopped(String type) { }
            public void onStartDiscoveryFailed(String type,int error) {
                handler.post(()->{ if(epoch==generation) { failure("browse",error); stopBrowse(); } });
            }
            public void onStopDiscoveryFailed(String type,int error) { failure("stop browse",error); }
            public void onServiceFound(NsdServiceInfo service) {
                handler.post(()->{
                    if(epoch!=generation || service.getServiceName().startsWith(prefix) || found.size()>=128) return;
                    String name=service.getServiceName();
                    if(found.containsKey(name)) return;
                    found.put(name,service); pending.add(service); resolveNext();
                });
            }
            public void onServiceLost(NsdServiceInfo service) {
                handler.post(()->{ if(epoch==generation) remove(service.getServiceName()); });
            }
        };
        try { nsd.discoverServices(TYPE,NsdManager.PROTOCOL_DNS_SD,browser); }
        catch(RuntimeException e) { browser=null; Log.w("ra3","[bonjour] browse",e); }
    }
    @SuppressWarnings("deprecation")
    private static java.net.InetAddress ipv4(NsdServiceInfo service) {
        if(android.os.Build.VERSION.SDK_INT>=34) {
            for(java.net.InetAddress address:service.getHostAddresses()) if(address instanceof Inet4Address) return address;
            return null;
        }
        return service.getHost() instanceof Inet4Address ? service.getHost() : null;
    }
    @SuppressWarnings("deprecation")
    private void resolveNext() {
        if(resolving || browser==null) return;
        NsdServiceInfo candidate;
        do { candidate=pending.poll(); } while(candidate!=null && found.get(candidate.getServiceName())!=candidate);
        if(candidate==null) return;
        final NsdServiceInfo request=candidate;
        final int epoch=generation;
        resolving=true;
        NsdManager.ResolveListener listener=new NsdManager.ResolveListener() {
            public void onResolveFailed(NsdServiceInfo service,int error) {
                handler.post(()->{ resolving=false; failure("resolve",error); resolveNext(); });
            }
            public void onServiceResolved(NsdServiceInfo service) {
                handler.post(()->{
                    resolving=false;
                    byte[] advertised=service.getAttributes().get("wire");
                    java.net.InetAddress host=ipv4(service);
                    if(epoch==generation && found.get(request.getServiceName())==request &&
                       advertised!=null && wire.equals(new String(advertised,StandardCharsets.UTF_8)) &&
                       host!=null && service.getPort()>=8086 && service.getPort()<=8093) {
                        String name=request.getServiceName(), address=host.getHostAddress();
                        addresses.put(name,address);
                        GameActivity.nativeBonjourPeer("android:"+name,address,service.getPort(),true);
                        Log.i("ra3","[bonjour] peer "+address+":"+service.getPort());
                    }
                    resolveNext();
                });
            }
        };
        try { nsd.resolveService(request,listener); }
        catch(RuntimeException e) { resolving=false; Log.w("ra3","[bonjour] resolve",e); handler.post(this::resolveNext); }
    }
}
