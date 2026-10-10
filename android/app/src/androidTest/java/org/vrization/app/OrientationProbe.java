package org.vrization.app;

import android.hardware.SensorManager;
import org.vrization.core.OrientationMath;

/** Synthetic matrix tests use Android's real landscape remap API, without reading any sensor. */
final class OrientationProbe {
    private OrientationProbe() { }
    static int run() {
        float[] identity={1,0,0,0,1,0,0,0,1};
        float[] origin=multiply(multiply(y(.3),x(.5)),z(-.2));
        float[][] motion={y(-Math.PI/2),x(Math.PI/2),multiply(multiply(y(-.7),x(-.4)),z(-.9))};
        float s=(float)Math.sqrt(.5);
        float[][] goldens={{0,-s,0,s},{s,0,0,s},{-.0218698503f,-.3837819133f,-.4617914703f,.7993633658f}};
        int[][] axes={{SensorManager.AXIS_X,SensorManager.AXIS_Y},
            {SensorManager.AXIS_Y,SensorManager.AXIS_MINUS_X},
            {SensorManager.AXIS_MINUS_X,SensorManager.AXIS_MINUS_Y},
            {SensorManager.AXIS_MINUS_Y,SensorManager.AXIS_X}};
        int count=0;
        for(int[] axis:axes)for(int n=0;n<motion.length;n++) {
            float[] basis=new float[9],baseline=new float[9],screen=new float[9];
            require(SensorManager.remapCoordinateSystem(identity,axis[0],axis[1],basis),"Identity remap failed");
            require(SensorManager.remapCoordinateSystem(origin,axis[0],axis[1],baseline),"Origin remap failed");
            float[] physical=multiply(multiply(multiply(origin,basis),motion[n]),transpose(basis));
            require(SensorManager.remapCoordinateSystem(physical,axis[0],axis[1],screen),"Motion remap failed");
            OrientationMath.Center center=new OrientationMath.Center();center.sample(baseline);
            float[] q=center.sample(screen); for(int k=0;k<4;k++)require(Math.abs(q[k]-goldens[n][k])<.000003,
                "Android landscape quaternion mismatch: sample="+n+" component="+k);
            count++;
        }
        return count;
    }
    private static float[] x(double a) {float c=(float)Math.cos(a),s=(float)Math.sin(a);return new float[]{1,0,0,0,c,-s,0,s,c};}
    private static float[] y(double a) {float c=(float)Math.cos(a),s=(float)Math.sin(a);return new float[]{c,0,s,0,1,0,-s,0,c};}
    private static float[] z(double a) {float c=(float)Math.cos(a),s=(float)Math.sin(a);return new float[]{c,-s,0,s,c,0,0,0,1};}
    private static float[] transpose(float[] m) {float[] out=new float[9];for(int r=0;r<3;r++)for(int c=0;c<3;c++)out[r*3+c]=m[c*3+r];return out;}
    private static float[] multiply(float[] a,float[] b) {
        float[] out=new float[9];for(int r=0;r<3;r++)for(int c=0;c<3;c++)for(int k=0;k<3;k++)out[3*r+c]+=a[3*r+k]*b[3*k+c];return out;
    }
    private static void require(boolean condition,String message) {if(!condition)throw new AssertionError(message);}
}
