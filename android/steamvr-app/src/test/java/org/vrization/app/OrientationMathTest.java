package org.vrization.app;

import org.junit.Test;
import org.vrization.core.OrientationMath;
import static org.junit.Assert.*;

public final class OrientationMathTest {
    private static final float EPS = 0.000002f;
    static final float[] I = {1,0,0,0,1,0,0,0,1};
    static float[] x(double a) { float c=(float)Math.cos(a),s=(float)Math.sin(a); return new float[]{1,0,0,0,c,-s,0,s,c}; }
    static float[] y(double a) { float c=(float)Math.cos(a),s=(float)Math.sin(a); return new float[]{c,0,s,0,1,0,-s,0,c}; }
    static float[] z(double a) { float c=(float)Math.cos(a),s=(float)Math.sin(a); return new float[]{c,-s,0,s,c,0,0,0,1}; }
    static float[] multiply(float[] a,float[] b) {
        float[] result=new float[9]; for(int r=0;r<3;r++)for(int c=0;c<3;c++)for(int k=0;k<3;k++)result[3*r+c]+=a[3*r+k]*b[3*k+c];
        return result;
    }
    @Test public void identityIsHamiltonXyzwWithScalarLast() { assertArrayEquals(new float[]{0,0,0,1},OrientationMath.quaternion(I),EPS); }
    @Test public void rightYaw90MatchesTheSharedOpenVrGolden() {
        float s=(float)Math.sqrt(.5); assertArrayEquals(new float[]{0,-s,0,s},OrientationMath.quaternion(y(-Math.PI/2)),EPS);
    }
    @Test public void upPitch90MatchesTheSharedOpenVrGolden() {
        float s=(float)Math.sqrt(.5); assertArrayEquals(new float[]{s,0,0,s},OrientationMath.quaternion(x(Math.PI/2)),EPS);
    }
    @Test public void clockwiseRoll90MatchesTheSharedOpenVrGolden() {
        float s=(float)Math.sqrt(.5); assertArrayEquals(new float[]{0,0,-s,s},OrientationMath.quaternion(z(-Math.PI/2)),EPS);
    }
    @Test public void all180DegreeBranchesRemainFiniteAndNormalized() {
        assertArrayEquals(new float[]{1,0,0,0},OrientationMath.quaternion(x(Math.PI)),EPS);
        assertArrayEquals(new float[]{0,1,0,0},OrientationMath.quaternion(y(Math.PI)),EPS);
        assertArrayEquals(new float[]{0,0,1,0},OrientationMath.quaternion(z(Math.PI)),EPS);
    }
    @Test public void compoundFullRotationMatchesIosWithoutReconstructingEulerAngles() {
        float[] matrix=multiply(multiply(y(-.7),x(-.4)),z(-.9));
        assertArrayEquals(new float[]{-.0218698503f,-.3837819133f,-.4617914703f,.7993633658f},OrientationMath.quaternion(matrix),EPS);
    }
    @Test public void arbitraryReferenceOriginCancelsBeforeTheCompoundMotion() {
        float[] origin=multiply(multiply(y(.3),x(.5)),z(-.2));
        float[] motion=multiply(multiply(y(-.7),x(-.4)),z(-.9));
        OrientationMath.Center center=new OrientationMath.Center();
        assertArrayEquals(new float[]{0,0,0,1},center.sample(origin),EPS);
        assertArrayEquals(new float[]{-.0218698503f,-.3837819133f,-.4617914703f,.7993633658f},center.sample(multiply(origin,motion)),EPS);
    }
    @Test public void landscapeBasesProduceTheSameMotionWhenRebasedInScreenCoordinates() {
        float[] portrait=multiply(y(.8),x(.3)), motion=multiply(y(-.7),z(-.4));
        for (double landscape : new double[]{Math.PI/2,-Math.PI/2}) {
            float[] screenBasis=z(landscape), baseline=multiply(portrait,screenBasis);
            float[] physical=multiply(baseline,motion); OrientationMath.Center center=new OrientationMath.Center();
            center.sample(baseline); assertArrayEquals(OrientationMath.quaternion(motion),center.sample(physical),EPS);
        }
    }
    @Test public void quaternionSignIsContinuousAcrossAFullRotationAndRecentersLocally() {
        OrientationMath.Center center=new OrientationMath.Center(); float[] previous=center.sample(I);
        for(int degrees=30;degrees<=360;degrees+=30) {
            float[] q=center.sample(y(Math.toRadians(degrees))); float dot=0;
            for(int n=0;n<4;n++)dot+=q[n]*previous[n]; assertTrue("Quaternion flipped sign at "+degrees,dot>.9);
            OrientationMath.validateQuaternion(q); previous=q;
        }
        assertEquals(-1,previous[3],EPS); center.recenter();
        assertArrayEquals(new float[]{0,0,0,1},center.sample(y(.8)),EPS);
    }
    @Test public void malformedAndReflectedMatricesNeverEstablishATrackingOrigin() {
        OrientationMath.Center center=new OrientationMath.Center();
        for(float[] bad:new float[][]{null,{1,0},{1,0,0,0,1,0,0,0,-1},{2,0,0,0,1,0,0,0,1},{Float.NaN,0,0,0,1,0,0,0,1}})
            assertThrows(IllegalArgumentException.class,()->center.sample(bad));
        assertArrayEquals(new float[]{0,0,0,1},center.sample(y(.7)),EPS);
    }
    @Test public void capturedOriginIsNotChangedByReusingTheSensorsMatrixBuffer() {
        float[] reusable=y(.7); OrientationMath.Center center=new OrientationMath.Center(); center.sample(reusable);
        System.arraycopy(y(.9),0,reusable,0,9);
        assertArrayEquals(new float[]{0,(float)Math.sin(.1),0,(float)Math.cos(.1)},center.sample(reusable),EPS);
    }
    @Test public void fullPitchPastTheEulerPolePreservesTheActualQuaternion() {
        OrientationMath.Center center=new OrientationMath.Center(); center.sample(I);
        for(double pitch:new double[]{1.5,Math.PI/2,1.7,2.0}) {
            assertArrayEquals(new float[]{(float)Math.sin(pitch/2),0,0,(float)Math.cos(pitch/2)},center.sample(x(pitch)),EPS);
        }
    }
}
